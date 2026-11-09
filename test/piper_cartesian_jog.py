#!/usr/bin/env python3
"""Keyboard Cartesian control of the Piper: move the da Vinci instrument tip with teleop_twist_keyboard.

Test tool, not part of the image: it is used to check the simulation (test/run_tests.sh) and can
serve as a starting point for your own control. To try it, copy it into the container and start
the simulation with --jog:
    docker cp test/piper_cartesian_jog.py piper-jazzy:/root/davinci_piper/
    docker exec piper-jazzy /root/davinci_piper/run_davinci_piper.sh --jog

Subscribes to a Twist (from teleop_twist_keyboard), moves a target pose of the instrument wrist
(frame instrument_wrist) in the Piper base frame, solves the inverse kinematics for joint1..joint6,
and publishes the joint positions on control/joint_states. In simulation robot_state_publisher reads
that topic; with the real arm the agx_arm driver reads it and moves the arm.

teleop_twist_keyboard keys (at its default speed 0.5 / turn 1.0):
    i / ,     instrument tip forward / back (base x)
    J / L     tip left / right (base y; shift = holonomic mode)
    t / b     tip up / down (base z)
    j / l     turn the instrument about the vertical axis through the tip
    k         stop
The shaft direction is otherwise held. The instrument's roll about its own shaft may drift a few
degrees while the arm moves: holding it exactly as well makes this 6-joint arm nearly singular, and
the roll key of the adaptor sets the roll anyway. When a step would leave the reachable range or
pass a joint limit, the step is refused and the arm stays where it is, so reversing the key moves
the arm at once.

From the starting pose the tip reaches roughly 240 mm forward, 115 mm back, 80 mm left, 120 mm
right, 95 mm up and 200 mm down, and the instrument turns only about 9 degrees each way: the
flange has to travel around the tip on a circle of about 0.3 m, and joint5 (+-70 degrees) runs out.

    python3 piper_cartesian_jog.py --ros-args -r cmd_vel:=/piper/cmd_vel
    python3 piper_cartesian_jog.py --ros-args -p seed_topic:=feedback/joint_states   # real arm: start from its current pose

Inverse kinematics: weighted damped least squares on the geometric Jacobian of the URDF chain from
the robot_description topic, so it uses the same model (adaptor and instrument offsets included) as
RViz. Errors are weighted 1 for tip position (metres), 0.3 for shaft direction (radians) and 0.02
for roll about the shaft.
"""

import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import String

JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
# Instrument wrist 0.48 m in front of the base, shaft 67 degrees below horizontal. Chosen by a search
# for the pose from which the keys reach furthest in every direction (reach is listed in the docstring).
READY_POSE = [0.154, 1.097, -1.151, 1.377, -0.792, 0.351]
# teleop_twist_keyboard's default speeds; a key press at those speeds moves at the full rate below.
KEYBOARD_LINEAR = 0.5
KEYBOARD_ANGULAR = 1.0
WEIGHTS = np.diag([1.0, 1.0, 1.0, 0.3, 0.3, 0.02])


def rpy_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr], [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr], [-sp, cp * sr, cp * cr]])


def axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def rotation_vector(r: np.ndarray) -> np.ndarray:
    """Axis times angle of a rotation matrix."""
    angle = np.arccos(np.clip((np.trace(r) - 1) / 2, -1.0, 1.0))
    if angle < 1e-9:
        return np.zeros(3)
    if angle > np.pi - 1e-6:
        # Near 180 degrees the formula below divides by ~0; the axis is the eigenvector with eigenvalue 1.
        values, vectors = np.linalg.eig(r)
        axis = np.real(vectors[:, np.argmin(np.abs(values - 1))])
        return axis / np.linalg.norm(axis) * angle
    return angle / (2 * np.sin(angle)) * np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])


class Chain:
    """Forward kinematics of the URDF joints between two links."""

    def __init__(self, urdf: str, base: str, tip: str) -> None:
        root = ET.fromstring(urdf)
        by_child = {j.find("child").get("link"): j for j in root.findall("joint")}
        joints, link = [], tip
        while link != base:
            joints.append(by_child[link])
            link = joints[-1].find("parent").get("link")
        self.steps = []  # (fixed 4x4 origin, joint index or None, axis)
        self.lower, self.upper = np.full(6, -np.pi), np.full(6, np.pi)
        for j in reversed(joints):
            origin = j.find("origin")
            xyz = [float(v) for v in (origin.get("xyz") if origin is not None and origin.get("xyz") else "0 0 0").split()]
            rpy = [float(v) for v in (origin.get("rpy") if origin is not None and origin.get("rpy") else "0 0 0").split()]
            t = np.eye(4)
            t[:3, :3], t[:3, 3] = rpy_matrix(*rpy), xyz
            index = JOINTS.index(j.get("name")) if j.get("type") == "revolute" else None
            axis = np.array([float(v) for v in j.find("axis").get("xyz").split()]) if j.find("axis") is not None else np.array([1.0, 0, 0])
            if index is not None:
                limit = j.find("limit")
                self.lower[index], self.upper[index] = float(limit.get("lower")), float(limit.get("upper"))
            self.steps.append((t, index, axis / np.linalg.norm(axis)))

    def fk(self, q: np.ndarray) -> np.ndarray:
        return self.fk_with_joints(q)[0]

    def fk_with_joints(self, q: np.ndarray) -> tuple:
        """Tool pose (4x4, base frame) and, for each moving joint, (index, axis, position) in the base frame."""
        t = np.eye(4)
        joints = []
        for origin, index, axis in self.steps:
            t = t @ origin
            if index is not None:
                joints.append((index, t[:3, :3] @ axis, t[:3, 3].copy()))
                rotation = np.eye(4)
                rotation[:3, :3] = axis_angle(axis, q[index])
                t = t @ rotation
        return t, joints

    def error(self, q: np.ndarray, target: np.ndarray) -> np.ndarray:
        """[position error (base frame, m), rotation error (tool frame, rad)]. In the tool frame the
        x and y rotation components tilt the shaft and z rolls the instrument about it."""
        t = self.fk(q)
        rotation = t[:3, :3].T @ rotation_vector(target[:3, :3] @ t[:3, :3].T)
        return np.concatenate([target[:3, 3] - t[:3, 3], rotation])

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        """Geometric Jacobian of revolute joints: column i is [z_i x (p_tool - p_i); R^T z_i], where z_i and
        p_i are the joint axis and position in the base frame. The angular part is turned into the tool
        frame to match error(). For the small errors of one control step it is the derivative of -error."""
        t, joints = self.fk_with_joints(q)
        jac = np.zeros((6, 6))
        for index, axis, position in joints:
            jac[:3, index] = np.cross(axis, t[:3, 3] - position)
            jac[3:, index] = t[:3, :3].T @ axis
        return jac


class PiperCartesianJog(Node):
    def __init__(self) -> None:
        super().__init__("piper_cartesian_jog")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("tool_frame", "instrument_wrist")
        self.declare_parameter("rate", 60.0)
        self.declare_parameter("linear_speed", 0.04)  # m/s at full key
        self.declare_parameter("angular_speed", 0.25)  # rad/s at full key
        self.declare_parameter("max_joint_speed", 1.0)  # rad/s per joint
        self.declare_parameter("seed_topic", "")  # e.g. feedback/joint_states to start from the real arm's pose

        self.dt = 1.0 / self.get_parameter("rate").value
        self.chain = None
        self.q = np.array(READY_POSE)
        self.target = None
        self.twist = np.zeros(6)
        self.waiting_for_seed = bool(self.get_parameter("seed_topic").value)

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "robot_description", self.on_description, latched)
        self.create_subscription(Twist, "cmd_vel", self.on_twist, 10)
        if self.waiting_for_seed:
            self.create_subscription(JointState, self.get_parameter("seed_topic").value, self.on_seed, 10)
        self.publisher = self.create_publisher(JointState, "control/joint_states", 10)
        self.create_timer(self.dt, self.update)
        self.get_logger().info("Waiting for robot_description" + (" and the arm's joint states" if self.waiting_for_seed else ""))

    def on_description(self, msg: String) -> None:
        if self.chain is None:
            self.chain = Chain(msg.data, self.get_parameter("base_frame").value, self.get_parameter("tool_frame").value)
            self.get_logger().info("Ready: i/, forward/back, J/L left/right, t/b up/down, j/l turn, k stop")

    def on_seed(self, msg: JointState) -> None:
        if self.waiting_for_seed and all(name in msg.name for name in JOINTS):
            self.q = np.array([msg.position[msg.name.index(name)] for name in JOINTS])
            self.waiting_for_seed = False
            self.target = None
            self.get_logger().info(f"Starting from the arm's pose {np.round(self.q, 3).tolist()}")

    def on_twist(self, msg: Twist) -> None:
        self.twist = np.array([msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.x, msg.angular.y, msg.angular.z])

    def update(self) -> None:
        if self.chain is None or self.waiting_for_seed:
            return
        if self.target is None:
            self.target = self.chain.fk(self.q)

        # Proposed target: translate in the base frame, turn about the vertical axis through the tip.
        linear = self.twist[:3] / KEYBOARD_LINEAR * self.get_parameter("linear_speed").value
        turn = self.twist[5] / KEYBOARD_ANGULAR * self.get_parameter("angular_speed").value
        proposed = self.target.copy()
        proposed[:3, 3] += linear * self.dt
        proposed[:3, :3] = axis_angle(np.array([0.0, 0.0, 1.0]), turn * self.dt) @ proposed[:3, :3]

        # Weighted damped least squares, a few iterations per tick, joint speed and limits enforced.
        q = self.q.copy()
        for _ in range(4):
            error = WEIGHTS @ self.chain.error(q, proposed)
            if np.linalg.norm(error) < 1e-6:
                break
            jac = WEIGHTS @ self.chain.jacobian(q)
            q = np.clip(q + jac.T @ np.linalg.solve(jac @ jac.T + 1e-5 * np.eye(6), error), self.chain.lower, self.chain.upper)
        max_step = self.get_parameter("max_joint_speed").value * self.dt
        q = self.q + np.clip(q - self.q, -max_step, max_step)

        # Take the step only if the arm reaches it (tip within 2 mm, shaft direction within 0.6 degrees);
        # otherwise stay, so the tip stops at the edge of the reachable range instead of sliding off.
        error = self.chain.error(q, proposed)
        if np.linalg.norm(error[:3]) < 0.002 and np.linalg.norm(error[3:5]) < 0.01:
            self.q, self.target = q, proposed
        elif np.any(self.twist):
            self.get_logger().warn(
                f"Arm cannot move further this way (tip {np.round(self.target[:3, 3], 3).tolist()} m, joints {np.round(self.q, 2).tolist()}); use the opposite key",
                throttle_duration_sec=2.0,
            )

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = JOINTS
        msg.position = self.q.tolist()
        self.publisher.publish(msg)


def main() -> None:
    rclpy.init()
    try:
        rclpy.spin(PiperCartesianJog())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
