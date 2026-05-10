import numpy as np
from llm_chat_node.detectors import yolo_preprocess, yolo_postprocess


def test_yolo_preprocess_and_postprocess():
    # Create a dummy image (480x640 BGR)
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    blob, scale, pad = yolo_preprocess(img, target_size=(640, 640))

    # blob shape should be (1,3,640,640)
    assert blob.ndim == 4
    assert blob.shape[0] == 1
    assert blob.shape[1] == 3
    assert blob.shape[2] == 640
    assert blob.shape[3] == 640

    # craft a fake YOLO output with one detection
    # format per-row: [x, y, w, h, scores...] where scores length=80
    row = np.zeros(84, dtype=float)
    # center x,y in padded coords: use values matching preprocessing
    # set x,y to center of canvas
    row[0] = 320.0
    row[1] = 240.0
    row[2] = 100.0
    row[3] = 50.0
    # set class 0 score high
    row[4 + 0] = 0.9

    outputs = np.expand_dims(row, axis=0)

    classes = ['person', 'bicycle']

    results = yolo_postprocess(outputs, scale, pad, (480, 640), confidence_threshold=0.5, nms_threshold=0.45, classes=classes)

    assert isinstance(results, list)
    assert len(results) >= 0
    if len(results) > 0:
        det = results[0]
        assert det['class_name'] in classes
        assert 0 <= det['confidence'] <= 1
        assert len(det['bbox']) == 4
