# AgileX Piper arm on ROS 2 Jazzy (Ubuntu 24.04) with the official agx_arm_ros driver, the
# da Vinci Si instrument adaptor on the arm, and the LapGym surgical scenes in SOFA.
#
# Build:  docker build -t piper-jazzy .
# Run:    ./run_piper.sh            (see that script for the docker run options)
#
# The driver, SDK, SOFA, LapGym and the adaptor model are pinned to the versions these
# instructions were tested with.
# To use the newest versions instead:
#   docker build -t piper-jazzy --build-arg AGX_ARM_ROS_REF=ros2 --build-arg PYAGXARM_REF=main .

FROM osrf/ros:jazzy-desktop

ARG AGX_ARM_ROS_REF=286633e0d2edb038ee3a1047d9feb7f614a1c076
ARG PYAGXARM_REF=d90e234ba8e408cfa964b38aa9120b3131fc9f85
# Set to true to also install MoveIt and build agx_arm_moveit (adds a few GB).
ARG WITH_MOVEIT=false

ENV DEBIAN_FRONTEND=noninteractive \
    LC_NUMERIC=en_US.UTF-8 \
    QT_X11_NO_MITSHM=1

# System and ROS 2 packages listed in the agx_arm_ros README.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git python3-pip can-utils ethtool iproute2 \
        python3-colcon-common-extensions \
        ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
        ros-jazzy-controller-manager ros-jazzy-topic-tools \
        ros-jazzy-joint-state-publisher-gui \
        ros-jazzy-robot-state-publisher ros-jazzy-xacro \
    && if [ "$WITH_MOVEIT" = "true" ]; then \
        apt-get install -y --no-install-recommends 'ros-jazzy-moveit*' \
            ros-jazzy-joint-trajectory-controller \
            ros-jazzy-gripper-controllers ros-jazzy-trajectory-msgs ; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# AgileX Python SDK. Ubuntu 24.04 needs --break-system-packages to pip-install into the system
# Python, which is the interpreter ROS launches nodes with.
RUN git clone https://github.com/agilexrobotics/pyAgxArm.git /opt/pyAgxArm \
    && git -C /opt/pyAgxArm checkout "$PYAGXARM_REF" \
    && pip3 install --no-cache-dir --break-system-packages /opt/pyAgxArm python-can scipy

# ROS 2 driver. The arm models (URDF, meshes) are in a git submodule.
WORKDIR /root/agx_arm_ws/src
RUN git clone -b ros2 https://github.com/agilexrobotics/agx_arm_ros.git \
    && git -C agx_arm_ros checkout "$AGX_ARM_ROS_REF" \
    && git -C agx_arm_ros submodule update --init --recursive

WORKDIR /root/agx_arm_ws
RUN . /opt/ros/jazzy/setup.sh \
    && if [ "$WITH_MOVEIT" = "true" ]; then colcon build; \
       else colcon build --packages-skip agx_arm_moveit; fi

# ---------------------------------------------------------------------------------------------
# SOFA surgical simulation (LapGym grasp_lift_touch and pick_and_place) with keyboard control
# through ROS 2, and the Piper with the da Vinci adaptor driving the instrument.
# Set WITH_SOFA=false to leave it out (saves about 3 GB).
# ---------------------------------------------------------------------------------------------
ARG WITH_SOFA=true
ARG SOFA_URL=https://github.com/sofa-framework/sofa/releases/download/v25.12.00/SOFA_v25.12.00_Linux-Python_3.12.zip
ARG SOFA_ENV_REF=85bf7e05dd088b824794dda0046679df13b13e6e

# Runtime libraries for SOFA's GUI-less build, OpenGL rendering, pygame and OpenCV,
# plus the keyboard teleop node and tmux for the launcher.
RUN if [ "$WITH_SOFA" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            wget unzip python3-venv tmux \
            libgl1 libglu1-mesa libglew2.2 libglib2.0-0 libxrender1 libxext6 libsm6 \
            ros-jazzy-teleop-twist-keyboard \
        && rm -rf /var/lib/apt/lists/* ; \
    fi

# SOFA v25.12 binary release built for Python 3.12 (the Python of Ubuntu 24.04).
RUN if [ "$WITH_SOFA" = "true" ]; then \
        wget -q -O /tmp/sofa.zip "$SOFA_URL" \
        && unzip -q /tmp/sofa.zip -d /tmp/sofa \
        && mv /tmp/sofa/SOFA_v25.12.00_Linux /opt/sofa \
        && rm -rf /tmp/sofa.zip /tmp/sofa ; \
    fi

# LapGym (sofa_env) in its own venv, so its NumPy 2 / OpenCV / open3d stack does not touch the
# system Python that ROS uses.
RUN if [ "$WITH_SOFA" = "true" ]; then \
        python3 -m venv /opt/sofa_venv \
        && /opt/sofa_venv/bin/pip install --no-cache-dir \
            numpy==2.4.2 scipy==1.17.1 gymnasium==1.2.3 pyglet==1.5.21 pygame==2.6.1 \
            PyOpenGL==3.1.7 PyOpenGL-accelerate==3.1.10 opencv-python==5.0.0.93 \
            matplotlib==3.10.8 numba==0.68.1 open3d==0.19.0 numpy-stl==4.1.3 \
            inputs==0.5 tqdm==4.67.3 filelock==3.25.2 requests \
        && git clone https://github.com/ScheiklP/sofa_env.git /opt/sofa_env \
        && git -C /opt/sofa_env checkout "$SOFA_ENV_REF" ; \
    fi

# The patch ports the LapGym scenes from SOFA v24.06 to v25.12 and NumPy 2, and gives the
# grasp_lift_touch and pick_and_place grippers an optional wrist joint and independently driven
# jaws (the degrees of freedom of the da Vinci adaptor). The scripts are the keyboard teleop scene,
# the da Vinci Piper scene, the ROS-to-UDP bridge, a smoke test and the launcher.
COPY sofa/ /opt/sofa_teleop/
RUN if [ "$WITH_SOFA" = "true" ]; then \
        git -C /opt/sofa_env apply /opt/sofa_teleop/sofa_env_sofa25.patch \
        && SKIP_SOFA=1 /opt/sofa_venv/bin/pip install --no-cache-dir --no-deps -e /opt/sofa_env \
        && install -m 755 /opt/sofa_teleop/sofa-python /usr/local/bin/sofa-python \
        && install -m 755 /opt/sofa_teleop/run_sofa_teleop.sh /usr/local/bin/run_sofa_teleop ; \
    fi

# Piper with the da Vinci adaptor (URDF, keyboard Cartesian control, pose bridge to SOFA) and its
# launcher run_davinci_piper. The launcher opens a terminal (xterm) and arranges the windows
# on screen with wmctrl and xprop (x11-utils).
# The adaptor mesh is the CAD model from the open-platform adaptor repository (GPL-3.0), downloaded
# here instead of being copied into this repository.
ARG ADAPTOR_REF=17e32f2ae6f6877831ebaec4b8f49800bb7edabe
COPY davinci/ /root/davinci_piper/
RUN if [ "$WITH_SOFA" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends xterm wmctrl x11-utils \
        && rm -rf /var/lib/apt/lists/* \
        && mkdir -p /root/davinci_piper/meshes \
        && wget -q -O /root/davinci_piper/meshes/davinci_si_adapter.stl \
            "https://raw.githubusercontent.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments/$ADAPTOR_REF/Da%20vinci%20si%20manipulator.stl" \
        && chmod 755 /root/davinci_piper/*.sh /root/davinci_piper/*.py \
        && ln -s /root/davinci_piper/run_davinci_piper.sh /usr/local/bin/run_davinci_piper ; \
    fi

# Every shell in the container has ROS 2 and the driver workspace loaded.
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /root/.bashrc \
    && echo 'source /root/agx_arm_ws/install/setup.bash' >> /root/.bashrc

CMD ["bash"]
