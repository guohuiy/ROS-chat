# Installation (Ubuntu)

This guide shows how to set up the development environment on Ubuntu 22.04/24.04.

1. Install ROS2 (Humble for 22.04, Jazzy for 24.04) following official docs.

2. Create Python virtualenv and install runtime dependencies:

```bash
python3 -m venv ~/ros-chat-venv
source ~/ros-chat-venv/bin/activate
pip install --upgrade pip
pip install -r src/llm_chat_node/requirements.txt
```

If you want pinned dependencies for reproducible installs, generate `requirements.txt` from `requirements.in` using `pip-tools`:

```bash
pip install pip-tools
./scripts/generate_requirements.sh
pip install -r src/llm_chat_node/requirements.txt
```

3. Install package in editable mode for development:

```bash
cd ~/Desktop/ros-chat
source /opt/ros/humble/setup.bash  # or jazzy
source ~/ros-chat-venv/bin/activate
pip install -e src/llm_chat_node
colcon build
source install/setup.bash
```

You can run the included check script to validate installation:

```bash
./scripts/check_ros_install.sh
```

4. Frontend:

```bash
cd frontend
npm ci
npm run dev
```
