"""Piper with the da Vinci adaptor in RViz, for the SOFA simulation.

    ros2 launch /root/davinci_piper/davinci_piper.launch.py                  # keyboard Cartesian control
    ros2 launch /root/davinci_piper/davinci_piper.launch.py arm:=sliders     # joint sliders
    ros2 launch /root/davinci_piper/davinci_piper.launch.py follow:=true     # real arm, see below

Starts robot_state_publisher with piper_davinci.urdf.xacro, RViz, and what moves the arm:
    arm:=keys      piper_cartesian_jog: teleop_twist_keyboard on /piper/cmd_vel moves the instrument tip
    arm:=sliders   joint_state_publisher_gui: one slider per joint
    arm:=none      nothing; use with follow:=true to watch the real arm moved by hand or another program
Both publish joint positions on control/joint_states, starting from a pose that holds the instrument
in front of the arm, shaft pointing forward and down.

follow:=false (default): the model in RViz (and so the SOFA instrument) shows control/joint_states.
follow:=true: it shows feedback/joint_states, which the agx_arm driver publishes from the real arm;
the driver also moves the real arm to what is published on control/joint_states, and
piper_cartesian_jog starts from the real arm's current pose.
"""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

HERE = Path(__file__).resolve().parent

# Same starting pose as piper_cartesian_jog.py: instrument wrist 0.48 m in front of the base, shaft 67 degrees below horizontal.
READY_POSE = {"joint1": 0.154, "joint2": 1.097, "joint3": -1.151, "joint4": 1.377, "joint5": -0.792, "joint6": 0.351}


def generate_launch_description() -> LaunchDescription:
    model = LaunchConfiguration("model")
    follow = LaunchConfiguration("follow")
    arm = LaunchConfiguration("arm")
    joint_topic = PythonExpression(["'feedback/joint_states' if '", follow, "' == 'true' else 'control/joint_states'"])
    seed_topic = PythonExpression(["'feedback/joint_states' if '", follow, "' == 'true' else ''"])
    rviz_config = HERE / "davinci_piper.rviz"  # 3D view only, no panels

    return LaunchDescription(
        [
            DeclareLaunchArgument("model", default_value=str(HERE / "piper_davinci.urdf.xacro"), description="robot model (xacro)"),
            DeclareLaunchArgument("follow", default_value="false", choices=["true", "false"], description="show the real arm's feedback"),
            DeclareLaunchArgument("arm", default_value="keys", choices=["keys", "sliders", "none"], description="what moves the arm"),
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
            Node(
                executable=str(HERE / "piper_cartesian_jog.py"),
                name="piper_cartesian_jog",
                output="screen",
                condition=IfCondition(PythonExpression(["'", arm, "' == 'keys'"])),
                parameters=[{"seed_topic": seed_topic}],
                remappings=[("cmd_vel", "/piper/cmd_vel")],
            ),
            Node(package="rviz2", executable="rviz2", arguments=["-d", str(rviz_config)]),
        ]
    )
