#!/usr/bin/env python3
"""Combine the Piper's joint states and the adaptor's joint states into joint_states for robot_state_publisher.

The arm joints (joint1 ... joint6) come from arm_topic: control/joint_states in simulation, or
feedback/joint_states, which the agx_arm driver publishes from the real arm. The adaptor joints
(instrument_roll, instrument_pitch, instrument_jaw_1, instrument_jaw_2) come from adapter_topic,
control/joint_states by default; the agx_arm driver ignores those names. An adaptor joint that has
not been published yet stays at its default below, so a program that only moves the arm still gets
the instrument in TF.

Publishes joint_states at `rate` Hz once the arm joints have arrived.

    python3 joint_state_merger.py --ros-args -p arm_topic:=feedback/joint_states
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState

ARM_JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
# Shaft roll and wrist pitch at zero, jaws open 20 degrees each way (radians).
ADAPTER_DEFAULTS = {"instrument_roll": 0.0, "instrument_pitch": 0.0, "instrument_jaw_1": 0.349, "instrument_jaw_2": -0.349}


def take(msg: JointState, target: dict, names) -> None:
    """Copy into target the positions of msg's joints that are in names."""
    for name, position in zip(msg.name, msg.position):
        if name in names:
            target[name] = position


class JointStateMerger(Node):
    def __init__(self) -> None:
        super().__init__("joint_state_merger")
        self.declare_parameter("arm_topic", "control/joint_states")
        self.declare_parameter("adapter_topic", "control/joint_states")
        self.declare_parameter("rate", 60.0)
        arm_topic = self.get_parameter("arm_topic").value
        adapter_topic = self.get_parameter("adapter_topic").value

        self.arm = {}
        self.adapter = dict(ADAPTER_DEFAULTS)
        if arm_topic == adapter_topic:
            self.create_subscription(JointState, arm_topic, lambda msg: (take(msg, self.arm, ARM_JOINTS), take(msg, self.adapter, ADAPTER_DEFAULTS)), 10)
        else:
            self.create_subscription(JointState, arm_topic, lambda msg: take(msg, self.arm, ARM_JOINTS), 10)
            self.create_subscription(JointState, adapter_topic, lambda msg: take(msg, self.adapter, ADAPTER_DEFAULTS), 10)
        self.publisher = self.create_publisher(JointState, "joint_states", 10)
        self.create_timer(1.0 / self.get_parameter("rate").value, self.publish)
        self.get_logger().info(f"Arm joints from {arm_topic}, adaptor joints from {adapter_topic}")

    def publish(self) -> None:
        if len(self.arm) < len(ARM_JOINTS):
            return
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ARM_JOINTS + list(self.adapter)
        msg.position = [self.arm[name] for name in ARM_JOINTS] + list(self.adapter.values())
        self.publisher.publish(msg)


def main() -> None:
    rclpy.init()
    try:
        rclpy.spin(JointStateMerger())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
