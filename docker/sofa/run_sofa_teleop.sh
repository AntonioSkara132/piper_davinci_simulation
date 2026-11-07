#!/usr/bin/env bash
# Keyboard control of the LapGym grasp-lift-touch gripper in SOFA, through ROS 2.
# Runs inside the piper-jazzy container (installed there as run_sofa_teleop).
#
# Starts a tmux session "sofa_teleop" with three panes:
#   1. the SOFA scene (window opens on the host desktop), listening on UDP port 5005
#   2. twist_socket_bridge: forwards /robot/cmd_vel as JSON over UDP to port 5005
#   3. teleop_twist_keyboard publishing to /robot/cmd_vel  <- type keys here
#
# Extra arguments go to the SOFA script, e.g.  run_sofa_teleop --speed 3 --width 1200
# (run  sofa-python /opt/sofa_teleop/lapgym_keyboard_teleop.py --help  for the full list).
# Stop everything with:  tmux kill-session -t sofa_teleop   (or Ctrl-b then : kill-session)
set -e
SESSION=sofa_teleop
APP=/opt/sofa_teleop
ROS_SETUP="source /opt/ros/jazzy/setup.bash"

SIM_CMD="sofa-python $APP/lapgym_keyboard_teleop.py --port 5005 $*"
BRIDGE_CMD="$ROS_SETUP && python3 $APP/twist_socket_bridge.py --ros-args -p port:=5005 --log-level warn"
TELEOP_CMD="$ROS_SETUP && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/robot/cmd_vel"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -x 200 -y 50 -n teleop "bash -c '$SIM_CMD; exec bash'"
tmux split-window -t "$SESSION" -v "bash -c '$BRIDGE_CMD; exec bash'"
tmux split-window -t "$SESSION" -v "bash -c '$TELEOP_CMD; exec bash'"
tmux select-layout -t "$SESSION" even-vertical
tmux select-pane -t "$SESSION":0.2   # the keyboard pane has the focus

if [ -t 1 ]; then
    exec tmux attach -t "$SESSION"
else
    echo "Started tmux session $SESSION; attach with: tmux attach -t $SESSION"
fi
