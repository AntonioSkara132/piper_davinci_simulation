from moveit_configs_utils import MoveItConfigsBuilder
import yaml
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path
from launch import LaunchDescription


def generate_launch_description():
    piper_servo_share = Path(get_package_share_directory("piper_servo"))
    # agx_arm_moveit's files are named agx_arm.*, so they must be given explicitly
    moveit_config = (
        MoveItConfigsBuilder("agx_arm", package_name="agx_arm_moveit")
        .robot_description(file_path="config/agx_arm.urdf.xacro")
        .robot_description_semantic(file_path="config/agx_arm.srdf.xacro")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    ld = LaunchDescription()

    servo_yaml_path = piper_servo_share / "config" / "piper_servo.yaml"
    with open(servo_yaml_path, 'r') as f:
        servo_yaml = yaml.safe_load(f)
        # agx_arm_moveit's move_group owns the planning scene
        servo_yaml["is_primary_planning_scene_monitor"] = False
        # agx_arm_moveit's ros2_control publishes the arm state here
        servo_yaml["joint_topic"] = "/control/joint_states"
        # agx's arm_controller rejects trajectories ending with nonzero velocity
        servo_yaml["publish_joint_velocities"] = False
        servo_params = {"moveit_servo": servo_yaml}

    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        output='screen',
        parameters=[
            moveit_config.to_dict(),
            servo_params,
            # required by the AccelerationLimitedPlugin smoothing filter
            {"update_period": servo_yaml["publish_period"],
             "planning_group_name": servo_yaml["move_group_name"]},
        ]
    )

    ld.add_action(servo_node)

    return ld
