#!/usr/bin/env python3
"""Send the da Vinci instrument's frames from TF to the SOFA simulation.

robot_state_publisher publishes TF from the Piper and adaptor joint states (the sliders in
simulation, or the real arm's feedback). This node reads, at `rate` Hz:
    base_link -> instrument_wrist           pose of the wrist at the end of the shaft (roll included)
    instrument_wrist -> instrument_clevis   wrist pitch, about y
    instrument_clevis -> instrument_jaw_1   jaw angles, about x
    instrument_clevis -> instrument_jaw_2
and sends them over UDP as JSON:

    {"tool_pose": [x, y, z, qx, qy, qz, qw],    metres, in the Piper base frame
     "pitch": deg, "jaws": [jaw_1 deg, jaw_2 deg]}

Runs with the system Python 3.12 and ROS 2 Jazzy; the SOFA script runs in its own venv, which is
why the frames go over UDP instead of rclpy.

    python3 piper_tool_bridge.py --ros-args -p port:=5006
"""

import json
import math
import socket

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def angle_about(rotation, axis: str) -> float:
    """Angle in degrees of a rotation about one axis of its parent frame (x, y or z), from its quaternion."""
    return math.degrees(2.0 * math.atan2(getattr(rotation, axis), rotation.w))


class PiperToolBridge(Node):
    def __init__(self) -> None:
        super().__init__("piper_tool_bridge")
        self.declare_parameter("port", 5006)
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("rate", 60.0)
        self.port = self.get_parameter("port").value
        self.base_frame = self.get_parameter("base_frame").value

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.warned = False
        self.create_timer(1.0 / self.get_parameter("rate").value, self.send)
        self.get_logger().info(f"Sending {self.base_frame} -> instrument_wrist, the wrist pitch and the jaws to UDP 127.0.0.1:{self.port}")

    def lookup(self, parent: str, child: str):
        return self.tf_buffer.lookup_transform(parent, child, Time()).transform

    def send(self) -> None:
        try:
            wrist = self.lookup(self.base_frame, "instrument_wrist")
            pitch = self.lookup("instrument_wrist", "instrument_clevis")
            jaw_1 = self.lookup("instrument_clevis", "instrument_jaw_1")
            jaw_2 = self.lookup("instrument_clevis", "instrument_jaw_2")
        except TransformException as error:
            if not self.warned:
                self.get_logger().warn(f"No transform yet ({error}); is robot_state_publisher running?")
                self.warned = True
            return
        t, q = wrist.translation, wrist.rotation
        payload = {
            "tool_pose": [t.x, t.y, t.z, q.x, q.y, q.z, q.w],
            "pitch": angle_about(pitch.rotation, "y"),
            "jaws": [angle_about(jaw_1.rotation, "x"), angle_about(jaw_2.rotation, "x")],
        }
        self.sock.sendto(json.dumps(payload).encode(), ("127.0.0.1", self.port))


def main() -> None:
    rclpy.init()
    try:
        rclpy.spin(PiperToolBridge())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
