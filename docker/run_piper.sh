#!/usr/bin/env bash
# Start (or re-enter) the Piper ROS 2 Jazzy container.
#
#   ./run_piper.sh              open a shell in the container
#   ./run_piper.sh <command>    run a command in it, e.g.
#   ./run_piper.sh ros2 launch agx_arm_description display.launch.py arm_type:=piper effector_type:=agx_gripper
#
# The container keeps running in the background between calls and keeps any changes you make.
# Delete it with: docker rm -f piper-jazzy
set -e
IMAGE=piper-jazzy
NAME=piper-jazzy

# Let local processes (including root inside the container) open windows on this display.
xhost +local: > /dev/null

if ! docker container inspect "$NAME" > /dev/null 2>&1; then
    # --net=host:      ROS 2 topics reach the host, and the container sees the host's can0
    # --privileged:    needed to bring the CAN interface up from inside the container
    # DISPLAY + X11:   RViz and the joint slider window open on the host desktop
    # /dev/dri:        hardware OpenGL for RViz and SOFA
    # core=0:          a crashing process exits at once instead of writing a core dump
    docker run -d --name "$NAME" \
        --net=host --privileged --ulimit core=0 \
        -e DISPLAY="$DISPLAY" \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        --device /dev/dri \
        "$IMAGE" sleep infinity > /dev/null
elif [ "$(docker container inspect -f '{{.State.Running}}' "$NAME")" != "true" ]; then
    docker start "$NAME" > /dev/null
fi

if [ $# -eq 0 ]; then
    exec docker exec -it "$NAME" bash
else
    exec docker exec -it "$NAME" bash -ic "$*"
fi
