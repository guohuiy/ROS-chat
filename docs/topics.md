# ROS Topics & Message Contracts

此文档列出前端与后端之间使用的 ROS 话题、消息类型以及示例负载，便于对接、测试与自动化。

## /chat_input
- 类型: `std_msgs/String`
- 方向: 前端/外部 → 后端
- 说明: 用户发送给 LLM 的文本问题或指令（纯文本）
- 示例:

```json
{"data": "你好，请介绍你自己"}
```

支持可选 JSON 格式以启用 per-client 限流：

```json
{"data": "{ \"client_id\": \"user123\", \"text\": \"请描述当前画面\" }"}
```

当发送 JSON 字符串时，节点会读取 `client_id` 用于限流控制，并使用 `text` 字段作为输入文本。

## /chat_output
- 类型: `std_msgs/String`
- 方向: 后端 → 前端/外部
- 说明: LLM 返回的完整文本回复
- 示例:

```json
{"data": "你好！我是一个基于 Ollama 的聊天机器人。"}
```

## /chat_output/stream
- 类型: `std_msgs/String`
- 方向: 后端 → 前端
- 说明: 流式输出分块（逐 token 或逐片段），用于前端打字机效果
- 示例:

```json
{"data": "这是来自模型的第一段流式输出"}
```

## /vision/detection
- 类型: `vision_msgs/Detection2DArray`
- 方向: 后端 → 前端
- 说明: 结构化的检测结果（每个检测包含 bbox 与置信度）
- 重要字段说明:
  - `header.stamp` 时间戳
  - `detections` 数组，每项包含 `bbox` 与 `results`
  - `results[0].hypothesis.class_id`：类别名或 ID
  - `results[0].hypothesis.score`：置信度（0.0-1.0）

## /vision/detection_text
- 类型: `std_msgs/String`
- 方向: 后端 → 前端 / LLMChatNode
- 说明: 将检测结果转为可读文本，便于注入 LLM 上下文
- 示例:

```json
{"data": "Current objects detected: person (0.98), laptop (0.89)"}
```

## /vision/trigger
- 类型: `std_msgs/String`
- 方向: 前端 → 后端
- 说明: 手动触发一次检测，消息内容可为任意字符串（例如 `detect`）
- 示例:

```json
{"data": "detect"}
```

## /vision/health
- 类型: `std_msgs/String`
- 方向: 后端 → 监控/前端
- 说明: 心跳/状态信息（JSON 编码），包含运行状态、detector 类型与 fps
- 示例:

```json
{"data": "{\"status\": \"running\", \"detector\": \"yolo\", \"fps\": 12}"}
```
