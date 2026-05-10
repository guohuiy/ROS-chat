#!/usr/bin/env bash
# Check that the package is discoverable after colcon build and source
set -e
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash || true
source install/setup.bash || true

# Check ros2 can find package
ros2 pkg prefix llm_chat_node && echo "llm_chat_node package found"

# Check nodes available (this checks entry points)
if command -v llm_chat_node >/dev/null 2>&1; then
  echo "llm_chat_node CLI available"
fi

