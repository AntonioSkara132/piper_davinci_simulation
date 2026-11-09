#!/bin/bash
# Simulation tests. Run inside a container made from the piper-jazzy image, with this directory
# mounted at /tmp/t2 and Xvfb, openbox and ffmpeg installed (see README.md here). Installs the test
# tools (install.sh) first.
# Prints PASS / FAIL lines; screenshots go to /tmp/shots/.
export DISPLAY=:99
source /opt/ros/jazzy/setup.bash
source /root/agx_arm_ws/install/setup.bash
mkdir -p /tmp/shots
bash /tmp/t2/install.sh
S="davinci_piper:teleop.0"
READY="0.154, 1.097, -1.151, 1.377, -0.792, 0.351"
NAMES="name: [joint1, joint2, joint3, joint4, joint5, joint6]"
ALL_NAMES="name: [joint1, joint2, joint3, joint4, joint5, joint6, instrument_roll, instrument_pitch, instrument_jaw_1, instrument_jaw_2]"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; }
check() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }
shot() { ffmpeg -v error -y -f x11grab -draw_mouse 0 -video_size 1920x1080 -i :99 -frames:v 1 "/tmp/shots/$1.png"; }
status() { tmux capture-pane -p -J -t "$S" -S -200 | grep "wrist at" | tail -1; }
wait_status() {  # wait until the SOFA pane prints a new status line (one every 5 s)
    local before; before=$(tmux capture-pane -p -J -t "$S" -S -200 | grep -c "wrist at")
    for _ in $(seq 40); do
        sleep 0.5
        [ "$(tmux capture-pane -p -J -t "$S" -S -200 | grep -c "wrist at")" -gt "$before" ] && return 0
    done
    return 1
}
start() {  # start run_davinci_piper with the given options and wait until SOFA prints status
    tmux kill-session -t davinci_piper 2>/dev/null; sleep 3
    bash -ic "run_davinci_piper $*" > /tmp/run.log 2>&1
    for _ in $(seq 90); do sleep 1; status | grep -q "wrist at" && return 0; done
    return 1
}
stop() { tmux kill-session -t davinci_piper 2>/dev/null; sleep 3; }
node_running() {  # the ROS graph takes a moment to settle, so ask a few times
    for _ in 1 2 3 4 5; do ros2 node list 2>/dev/null | grep -qx "$1" && return 0; sleep 1; done
    return 1
}
pub_joints() {  # pub_joints <topic> <seconds> <positions> [names]
    timeout "$2" ros2 topic pub -r 20 "$1" sensor_msgs/msg/JointState "{header: auto, ${4:-$NAMES}, position: [$3]}" > /dev/null 2>&1
}
wrist() { status | grep -o 'wrist at \[[^]]*\]'; }

echo "=== A: ring scene, --jog (ARM keys and INSTRUMENT keys), tiling, grasp, reset"
check "A1 ring scene starts" "start --rings --jog"
sleep 8
shot A_start
check "A2 nodes running" "node_running /piper_cartesian_jog && node_running /robot_state_publisher && node_running /piper_tool_bridge && node_running /rviz"
check "A3 SOFA window placed on the left half" "wmctrl -lG | grep 'LapGym pick-and-place' | awk '{exit !(\$3 <= 5 && \$5 >= 900 && \$5 <= 970)}'"
check "A4 RViz top right" "wmctrl -lG | grep ' - RViz' | awk '{exit !(\$3 >= 950)}'"
check "A5 keys terminal open" "wmctrl -l | grep -q 'Da Vinci Piper keys'"
wmctrl -lG
check "A6 status line starts at the ready pose" "status | grep -q 'wrist at \[0.0, 65.0, 20.0\]'"
python3 /tmp/t2/moves.py grasp
wait_status; wait_status
status
check "A7 ring grasped through /piper/cmd_vel and /davinci/cmd_vel" "status | grep -q ' grasped' && status | grep -qv 'not grasped'"
shot A_grasped
python3 /tmp/t2/moves.py lift
wait_status
check "A8 still grasped after lifting" "status | grep -q ' grasped' && status | grep -qv 'not grasped'"
p1=$(wrist)
tmux send-keys -t "$S" r Enter
sleep 3; wait_status; wait_status
status
check "A9 reset: ring released, instrument back where the arm holds it" "status | grep -q 'not grasped' && [ \"\$(wrist)\" = \"\$p1\" ]"
sleep 2; shot A_after_reset
# ARM keys pane: a real key press through teleop_twist_keyboard
p1=$(wrist)
tmux send-keys -t davinci_piper:teleop.1 t; sleep 1; tmux send-keys -t davinci_piper:teleop.1 k
sleep 1; wait_status
status
check "A10 ARM key t moves the wrist" "[ \"\$(wrist)\" != \"\$p1\" ]"
tmux send-keys -t davinci_piper:teleop.2 L; sleep 1; tmux send-keys -t davinci_piper:teleop.2 k
sleep 1; wait_status
status
check "A11 INSTRUMENT key L opens the jaws (jaw_1 > 0)" "status | grep -oE 'jaws +-?[0-9]+' | awk '{exit !(\$2 > 0)}'"
tmux send-keys -t davinci_piper:teleop.2 i; sleep 1; tmux send-keys -t davinci_piper:teleop.2 k
sleep 1; wait_status
status
check "A12 INSTRUMENT key i pitches the wrist (pitch > 20)" "status | grep -oE 'pitch +-?[0-9]+' | awk '{exit !(\$2 > 20)}'"
stop

echo "=== B: organ scene"
check "B1 organ scene starts" "start --jog"
sleep 5
check "B2 SOFA window title" "wmctrl -l | grep -q 'LapGym grasp-lift-touch'"
before=$(status)
python3 /tmp/t2/moves.py down
wait_status
echo "$before"; status
check "B3 /piper/cmd_vel moves the instrument" "[ \"\$(status | grep -o 'wrist at \[[^]]*\]')\" != \"\$(echo \"\$before\" | grep -o 'wrist at \[[^]]*\]')\" ]"
shot B_organ
stop

echo "=== C: joint sliders (the default)"
check "C1 starts without options" "start --rings"
sleep 5
check "C2 joint_state_publisher_gui running, no jog" "node_running /joint_state_publisher && ! node_running /piper_cartesian_jog"
check "C3 slider window placed bottom right" "sleep 3; wmctrl -lG | grep 'Joint State Publisher' | awk '{exit !(\$3 >= 950 && \$4 >= 500)}'"
wmctrl -lG
shot C_sliders
stop

echo "=== D: --no-arm, your own JointState on /control/joint_states"
check "D1 starts with --no-arm" "start --rings --no-arm"
check "D2 nothing publishes joint states" "! node_running /piper_cartesian_jog && ! node_running /joint_state_publisher"
pub_joints /control/joint_states 8 "$READY"
wait_status; s1=$(status | grep -o 'wrist at \[[^]]*\]'); echo "$s1"
pub_joints /control/joint_states 8 "0.254, 1.097, -1.151, 1.377, -0.792, 0.351"
wait_status; s2=$(status | grep -o 'wrist at \[[^]]*\]'); echo "$s2"
check "D3 SOFA follows the published joint states" "status | grep -qv 'no instrument frames' && [ \"\$s1\" != \"\$s2\" ]"
check "D4 adaptor joints at their defaults (pitch 0, jaws 20 -20)" "status | grep -q 'pitch 0  jaws 20 -20'"
pub_joints /control/joint_states 8 "$READY, 0.5, 0.6, 0.2, -0.4" "$ALL_NAMES"
wait_status; status
check "D5 pitch and jaws come from the adaptor joints over TF" "status | grep -q 'pitch 34  jaws 11 -23'"
stop

echo "=== E: --follow without a real arm (fake feedback)"
check "E1 starts with --follow --jog" "start --rings --follow --jog"
pub_joints /feedback/joint_states 6 "$READY" &
FB=$!
sleep 3
python3 /tmp/t2/moves.py up_short
check "E2 jog publishes on /control/joint_states after feedback" "timeout 5 ros2 topic echo --once /control/joint_states > /dev/null 2>&1"
kill $FB 2>/dev/null
wait_status; status
check "E3 SOFA shows the feedback pose" "status | grep -qv 'no instrument frames'"
stop

echo "=== F: all 14 LapGym scenes"
sofa-python /opt/sofa_teleop/smoke_test.py > /tmp/smoke.log 2>&1
tail -16 /tmp/smoke.log
check "F1 smoke test passes" "! grep -qE 'FAIL|Traceback' /tmp/smoke.log"

echo "=== G: run_sofa_teleop (LapGym gripper without the Piper)"
bash -ic "run_sofa_teleop --width 950 --height 1050 --x 0 --y 0" > /tmp/sofa_teleop.log 2>&1
for _ in $(seq 60); do sleep 1; wmctrl -l | grep -q "LapGym grasp-lift-touch" && break; done
xterm -T "sofa_teleop" -geometry 120x60+960+0 -fa Monospace -fs 10 -bg black -fg white -e tmux attach -t sofa_teleop &
sleep 5
# tilt forward, then push in, through the keyboard pane
tmux send-keys -t sofa_teleop:0.2 i; sleep 2; tmux send-keys -t sofa_teleop:0.2 t; sleep 2; tmux send-keys -t sofa_teleop:0.2 k
sleep 2
check "G1 window opens" "wmctrl -l | grep -q 'LapGym grasp-lift-touch'"
tmux capture-pane -p -J -t sofa_teleop:teleop.0 | grep -v '^ *$' | tail -3
check "G2 no Python error" "! tmux capture-pane -p -J -t sofa_teleop:teleop.0 -S -200 | grep -q Traceback"
shot G_sofa_teleop
tmux kill-session -t sofa_teleop; pkill xterm; sleep 2
bash -ic "run_sofa_teleop --rings" > /tmp/sofa_teleop.log 2>&1
for _ in $(seq 60); do sleep 1; wmctrl -l | grep -q "LapGym pick-and-place" && break; done
sleep 5
check "G3 --rings opens the ring scene" "wmctrl -l | grep -q 'LapGym pick-and-place'"
check "G4 no Python error with --rings" "! tmux capture-pane -p -J -t sofa_teleop:teleop.0 -S -200 | grep -q Traceback"
tmux kill-session -t sofa_teleop; sleep 2

echo "=== H: the model in RViz with joint sliders (what is in the image, without the test tools)"
source /opt/ros/jazzy/setup.bash
ros2 launch /root/davinci_piper/davinci_piper.launch.py > /tmp/model.log 2>&1 &
LAUNCH=$!
for _ in $(seq 60); do sleep 1; wmctrl -l | grep -q "Joint State Publisher" && wmctrl -l | grep -q " - RViz" && break; done
sleep 5
check "H1 RViz and slider windows open" "wmctrl -l | grep -q 'Joint State Publisher' && wmctrl -l | grep -q ' - RViz'"
check "H2 TF base_link -> instrument_wrist" "timeout 10 ros2 run tf2_ros tf2_echo base_link instrument_wrist 2>/dev/null | grep -q Translation"
check "H3 TF base_link -> instrument_jaw_1" "timeout 10 ros2 run tf2_ros tf2_echo base_link instrument_jaw_1 2>/dev/null | grep -q Translation"
r=$(wmctrl -l | awk '/ - RViz/ {print $1; exit}'); s=$(wmctrl -l | awk '/Joint State Publisher/ {print $1; exit}')
wmctrl -i -r "$r" -e 0,0,0,1500,1050; wmctrl -i -r "$s" -e 0,1510,0,400,1050
sleep 3
shot H_model_sliders
kill $LAUNCH; sleep 3
echo "=== done"
