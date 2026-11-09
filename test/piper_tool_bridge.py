"""Send the pose of the da Vinci instrument on the Piper to the SOFA simulation.

Reads the transform base_link -> instrument_wrist from TF (published by robot_state_publisher from
the Piper joint states, so it follows the joint sliders in simulation or the real arm's feedback),
and sends it over UDP as JSON:

    {"tool_pose": [x, y, z, qx, qy, qz, qw]}     metres, in the Piper base frame

Runs with the system Python 3.12 and ROS 2 Jazzy; the SOFA script runs in its own venv, which is
why the pose goes over UDP instead of rclpy (same arrangement as twist_socket_bridge).

    python3 piper_tool_bridge.py --ros-args -p port:=5005
"""

import json
import socket

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


class PiperToolBridge(Node):
    def __init__(self) -> None:
        super().__init__("piper_tool_bridge")
        self.declare_parameter("port", 5005)
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("tool_frame", "instrument_wrist")
        self.declare_parameter("rate", 60.0)

        self.port = self.get_parameter("port").value
        self.base_frame = self.get_parameter("base_frame").value
        self.tool_frame = self.get_parameter("tool_frame").value

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.warned = False
        self.create_timer(1.0 / self.get_parameter("rate").value, self.send_pose)
        self.get_logger().info(f"Sending {self.base_frame} -> {self.tool_frame} to UDP 127.0.0.1:{self.port}")

    def send_pose(self) -> None:
        try:
            transform = self.tf_buffer.lookup_transform(self.base_frame, self.tool_frame, Time())
        except TransformException as error:
            if not self.warned:
                self.get_logger().warn(f"No transform yet ({error}); is robot_state_publisher running?")
                self.warned = True
            return
        t, q = transform.transform.translation, transform.transform.rotation
        payload = {"tool_pose": [t.x, t.y, t.z, q.x, q.y, q.z, q.w]}
        self.sock.sendto(json.dumps(payload).encode(), ("127.0.0.1", self.port))


def main() -> None:
    rclpy.init()
    try:
        rclpy.spin(PiperToolBridge())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
