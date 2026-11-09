#!/usr/bin/env bash
# The Piper with the da Vinci adaptor driving the instrument in a SOFA scene, grasp-lift-touch
# (organ, the default) or pick-and-place (rings, with --rings). From the host:
#     docker exec piper-jazzy run_davinci_piper [options]
#
# The instrument in SOFA follows TF: davinci_piper.launch.py (robot_state_publisher, by default with
# one slider per joint of the Piper and the adaptor) -> TF -> piper_tool_bridge.py -> UDP ->
# davinci_piper_scene.py. Opens a terminal on the tmux session and tiles it with the SOFA, RViz and
# slider windows over the whole screen (tile_windows.sh).
#
# tmux session "davinci_piper", window "teleop" (shown in the terminal; click a pane to type in it):
#     SOFA          the simulation's messages; r + Enter resets the scene
#     ARM keys, INSTRUMENT keys   only with --jog (test tool)
# window "ros" (Ctrl-b n): the ROS launch and piper_tool_bridge (and the jog).
# Stop everything with:  docker exec piper-jazzy tmux kill-session -t davinci_piper
#
# Options:
#     --rings       ring scene (pick-and-place) instead of the organ scene
#     --no-arm      no sliders; your program publishes control/joint_states
#     --follow      real arm: show its feedback, and the sliders move it (start the agx_arm driver first)
#     --jog         keyboard instead of sliders, through piper_cartesian_jog.py (installed from test/)
#     --no-tile     do not open the terminal or move windows; attach yourself
#     anything else goes to the SOFA script, e.g. --base X Y Z QX QY QZ QW
#
# Uses UDP port 5006 (and the topics /piper/cmd_vel, /davinci/cmd_vel with --jog), so it can run next
# to run_sofa_teleop (port 5005, /robot/cmd_vel).
set -e
SESSION=davinci_piper
HERE=/root/davinci_piper
APP=/opt/sofa_teleop
PORT=5006
ROS_SETUP="source /opt/ros/jazzy/setup.bash && source /root/agx_arm_ws/install/setup.bash"

FOLLOW=false
ARM=sliders
TILE=true
SIM_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --follow) FOLLOW=true ;;
        --sliders) ARM=sliders ;;  # the default
        --jog) ARM=keys ;;
        --no-arm) ARM=none ;;
        --no-tile) TILE=false ;;
        --rings) SIM_ARGS+=(--scene rings) ;;
        *) SIM_ARGS+=("$arg") ;;
    esac
done
if [ "$ARM" = keys ] && [ ! -f "$HERE/piper_cartesian_jog.py" ]; then
    echo "--jog needs piper_cartesian_jog.py; install the test tools with test/install.sh" >&2
    exit 1
fi

# The SOFA window starts on the left half of the screen; tile_windows.sh corrects it if needed.
SIM_CMD="sofa-python $APP/davinci_piper_scene.py --port $PORT --x 0 --y 27 --width 960 --height 1140 ${SIM_ARGS[*]}"
# The launch file only knows sliders and none; the jog is started here next to it.
LAUNCH_ARM=$ARM
[ "$ARM" = keys ] && LAUNCH_ARM=none
LAUNCH_CMD="$ROS_SETUP && ros2 launch $HERE/davinci_piper.launch.py follow:=$FOLLOW arm:=$LAUNCH_ARM"
POSE_CMD="$ROS_SETUP && python3 $HERE/piper_tool_bridge.py --ros-args -p port:=$PORT"
SEED_ARG=""
[ "$FOLLOW" = true ] && SEED_ARG="-p seed_topic:=feedback/joint_states"
JOG_CMD="$ROS_SETUP && python3 $HERE/piper_cartesian_jog.py --ros-args -r cmd_vel:=/piper/cmd_vel $SEED_ARG"
ARM_KEYS_CMD="$ROS_SETUP && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/piper/cmd_vel"
TOOL_KEYS_CMD="$ROS_SETUP && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/davinci/cmd_vel"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -x 200 -y 50 -n teleop "bash -c '$SIM_CMD; exec bash'"
tmux set -t "$SESSION" mouse on
tmux set -t "$SESSION" pane-border-status top
tmux set -t "$SESSION" pane-border-format " #{pane_title} "
tmux select-pane -t "$SESSION":teleop.0 -T "SOFA  (r+Enter reset)"
if [ "$ARM" = keys ]; then
    pane=$(tmux split-window -t "$SESSION":teleop -v -P -F '#{pane_id}' "bash -c '$ARM_KEYS_CMD; exec bash'")
    tmux select-pane -t "$pane" -T "ARM keys: i/, forward/back  J/L left/right  t/b up/down  j/l turn  k stop"
    pane=$(tmux split-window -t "$SESSION":teleop -v -P -F '#{pane_id}' "bash -c '$TOOL_KEYS_CMD; exec bash'")
    tmux select-pane -t "$pane" -T "INSTRUMENT keys: j/l roll  i/, wrist pitch  t/b wrist yaw  J/L close/open  k stop"
    tmux select-layout -t "$SESSION":teleop even-vertical
    tmux select-pane -t "$SESSION":teleop.1
fi
tmux new-window -d -t "$SESSION" -n ros "bash -c '$LAUNCH_CMD; exec bash'"
tmux split-window -t "$SESSION":ros -v "bash -c '$POSE_CMD; exec bash'"
if [ "$ARM" = keys ]; then
    tmux split-window -t "$SESSION":ros -v "bash -c '$JOG_CMD; exec bash'"
fi
tmux select-layout -t "$SESSION":ros even-vertical
tmux select-window -t "$SESSION":teleop

if [ "$TILE" = true ] && [ -n "${DISPLAY:-}" ]; then
    setsid "$HERE/tile_windows.sh" "$ARM" > /tmp/tile_windows.log 2>&1 < /dev/null &
    echo "Started tmux session $SESSION; the terminal and windows open in a few seconds."
elif [ -t 1 ]; then
    exec tmux attach -t "$SESSION"
else
    echo "Started tmux session $SESSION; attach with: tmux attach -t $SESSION"
fi
