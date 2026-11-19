# piper_servo

MoveIt Servo for the AgileX Piper on ROS 2 Jazzy. This package starts only `servo_node`.
The arm, its controllers, move_group and RViz come from the agx_arm packages in `~/agx_arm_ws`.

## Build

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash
cd ~/piper_servo_ws
colcon build --symlink-install
source install/setup.bash
```

## Run

```bash
# 1. The arm. Simulation:
ros2 launch agx_arm_moveit demo.launch.py
#    or the real arm:
ros2 launch agx_arm_ctrl start_single_agx_arm_moveit.launch.py can_port:=can0 arm_type:=piper

# 2. Servo
ros2 launch piper_servo piper_servo.launch.py

# 3. Keyboard teleop
ros2 run piper_servo keyboard_teleop.py
```

The agx arm starts at all-zero joints, where Servo won't do Cartesian motion. Jog a few joints
first (including joint5), or Plan & Execute to another pose in RViz.

## How it fits together

Servo reads the arm state from `/control/joint_states` and sends trajectories to
`/arm_controller/joint_trajectory`. Both come from agx_arm_moveit's ros2_control setup. With the
real arm, `agx_arm_ctrl` forwards `/control/joint_states` to the arm over CAN.

Servo settings are in `config/piper_servo.yaml`. The launch file overrides three of them:
- `joint_topic`: set to `/control/joint_states`
- `publish_joint_velocities`: set to `false`, because agx's `arm_controller` rejects trajectories
  that end with a nonzero velocity
- `is_primary_planning_scene_monitor`: set to `false`, because agx's move_group owns the
  planning scene

## Teleop

`keyboard_teleop.py`: arrow keys move X/Y, `.`/`,` move Z down/up, `1`–`6` jog a joint, `r` reverses
the joint direction, `w`/`e` switch to the base/end-effector frame, and `q` quits. It switches
Servo's command type automatically.

From your own code, publish `geometry_msgs/TwistStamped` to `/servo_node/delta_twist_cmds` or
`control_msgs/JointJog` to `/servo_node/delta_joint_cmds`. First call
`/servo_node/switch_command_type` (`moveit_msgs/srv/ServoCommandType`: 0 = joint jog, 1 = twist).
