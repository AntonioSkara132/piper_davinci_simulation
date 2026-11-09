"""Piper with the da Vinci adaptor in RViz.

    ros2 launch /root/davinci_piper/davinci_piper.launch.py                  # joint sliders
    ros2 launch /root/davinci_piper/davinci_piper.launch.py arm:=none        # your program moves the arm
    ros2 launch /root/davinci_piper/davinci_piper.launch.py follow:=true     # real arm, see below

Starts robot_state_publisher with piper_davinci.urdf.xacro, RViz, and what moves the arm:
    arm:=sliders   joint_state_publisher_gui: one slider per joint (default), published on
                   control/joint_states, starting from a pose that holds the instrument in front of
                   the arm, shaft pointing forward and down
    arm:=none      nothing; your program publishes control/joint_states
robot_state_publisher then publishes TF from base_link to instrument_wrist (the tip of the instrument).

follow:=false (default): the model in RViz shows control/joint_states.
follow:=true: it shows feedback/joint_states, which the agx_arm driver publishes from the real arm;
the driver also moves the real arm to what is published on control/joint_states, so the sliders
move the real arm.
"""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

HERE = Path(__file__).resolve().parent

# Starting pose of the sliders: instrument wrist 0.48 m in front of the base, shaft 67 degrees below horizontal.
READY_POSE = {"joint1": 0.154, "joint2": 1.097, "joint3": -1.151, "joint4": 1.377, "joint5": -0.792, "joint6": 0.351}


def generate_launch_description() -> LaunchDescription:
    model = LaunchConfiguration("model")
    follow = LaunchConfiguration("follow")
    arm = LaunchConfiguration("arm")
    joint_topic = PythonExpression(["'feedback/joint_states' if '", follow, "' == 'true' else 'control/joint_states'"])
    rviz_config = HERE / "davinci_piper.rviz"  # 3D view only, no panels

    return LaunchDescription(
        [
            DeclareLaunchArgument("model", default_value=str(HERE / "piper_davinci.urdf.xacro"), description="robot model (xacro)"),
            DeclareLaunchArgument("follow", default_value="false", choices=["true", "false"], description="show the real arm's feedback"),
            DeclareLaunchArgument("arm", default_value="sliders", choices=["sliders", "none"], description="what moves the arm"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": ParameterValue(Command(["xacro ", model]), value_type=str)}],
                remappings=[("joint_states", joint_topic)],
            ),
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                condition=IfCondition(PythonExpression(["'", arm, "' == 'sliders'"])),
                parameters=[{"rate": 60, **{f"zeros.{name}": value for name, value in READY_POSE.items()}}],
                remappings=[("joint_states", "control/joint_states")],
            ),
            Node(package="rviz2", executable="rviz2", arguments=["-d", str(rviz_config)]),
        ]
    )
