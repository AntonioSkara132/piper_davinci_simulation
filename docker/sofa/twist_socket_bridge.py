import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import socket
import json

class ExternalBridge(Node):
    def __init__(self):
        super().__init__('sofa_bridge')

        self.declare_parameter('port', 5005)
        self.port = self.get_parameter('port').value
        self.sub = self.create_subscription(Twist, '/robot/cmd_vel', self.listener_callback, 10)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.get_logger().info(f"Twist socket bridge initialized with port {self.get_parameter('port').value}")

    def listener_callback(self, msg):
        v = msg.linear
        w = msg.angular
        payload = {"vel": [v.x, v.y, v.z, w.x, w.y, w.z]}
        self.sock.sendto(json.dumps(payload).encode(), ('127.0.0.1', self.get_parameter('port').value))
        self.get_logger().info(f'Velocity message sent via {self.port}')
    
        

def main():
    rclpy.init()
    rclpy.spin(ExternalBridge())

if __name__ == '__main__':
    main()
    
