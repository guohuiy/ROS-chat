"""Utilities for YOLO preprocessing and postprocessing, extracted for testing.
"""
from typing import Tuple, List
import cv2
import numpy as np


def yolo_preprocess(image: np.ndarray, target_size=(640, 640)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """Resize image with letterbox and convert to blob for YOLO ONNX input.

    Returns (blob, scale, (pad_x, pad_y)). Blob is NCHW float32.
    """
    h, w = image.shape[:2]
    target_w, target_h = target_size

    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(image, (new_w, new_h))

    canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

    # blobFromImage returns shape (1,3,H,W)
    blob = cv2.dnn.blobFromImage(canvas, 1/255.0, swapRB=True, crop=False)

    return blob.astype(np.float32), scale, (pad_x, pad_y)


def yolo_postprocess(outputs: np.ndarray, scale: float, pad: Tuple[int, int], orig_shape: Tuple[int, int],
                     confidence_threshold: float = 0.5, nms_threshold: float = 0.45,
                     classes: List[str] = None) -> List[dict]:
    """Postprocess raw YOLO outputs into detection dicts.

    `outputs` should be shaped (N, 84) or (84, N); the function handles transposed variants.
    Returns list of {class_id, class_name, confidence, bbox:[x,y,w,h]} with coords in original image space.
    """
    if classes is None:
        classes = []

    # Normalize outputs shape to (rows, 84)
    if outputs.ndim == 3:
        # some runtimes give (1,84,8400) -> take first dimension
        outputs = outputs[0]
    if outputs.shape[0] < outputs.shape[1]:
        outputs = outputs.T

    rows = outputs.shape[0]
    boxes, scores, class_ids = [], [], []
    h_img, w_img = orig_shape

    for i in range(rows):
        row = outputs[i]
        classes_scores = row[4:]
        max_score = float(classes_scores.max())
        if max_score >= confidence_threshold:
            class_id = int(classes_scores.argmax())
            x, y, w, h = row[:4]
            x1 = int((x - w/2 - pad[0]) / scale)
            y1 = int((y - h/2 - pad[1]) / scale)
            x2 = int((x + w/2 - pad[0]) / scale)
            y2 = int((y + h/2 - pad[1]) / scale)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_img, x2), min(h_img, y2)
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(float(max_score))
            class_ids.append(class_id)

    # NMS
    results = []
    if len(boxes) > 0:
        try:
            indices = cv2.dnn.NMSBoxes(boxes, scores, confidence_threshold, nms_threshold)
            inds = indices.flatten() if len(indices) > 0 else []
        except Exception:
            inds = list(range(len(boxes)))

        for i in inds:
            cid = class_ids[i]
            cname = classes[cid] if cid < len(classes) else str(cid)
            results.append({
                'class_id': cid,
                'class_name': cname,
                'confidence': scores[i],
                'bbox': boxes[i],
            })

    return results


def try_init_onnxruntime_session(model_path: str):
    """Attempt to create an ONNX Runtime InferenceSession. Returns session object on success.
    Raises ImportError if onnxruntime is not available, or any exception from InferenceSession.
    """
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        return session
    except ImportError:
        raise
    except Exception:
        raise
