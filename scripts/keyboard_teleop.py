#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from control_msgs.msg import JointJog
from moveit_msgs.srv import ServoCommandType

import sys
import threading
import termios
import tty

# Key Definitions
class KeyCode:
    UP = '\x1b[A'
    DOWN = '\x1b[B'
    RIGHT = '\x1b[C'
    LEFT = '\x1b[D'
    PERIOD = '.'
    SEMICOLON = ','
    K1 = '1'
    K2 = '2'
    K3 = '3'
    K4 = '4'
    K5 = '5'
    K6 = '6'
    REVERSE = 'r'
    FRAME_BASE = 'w'
    FRAME_EE = 'e'
    QUIT = 'q'

class KeyboardServo(Node):
    def __init__(self):
        super().__init__('servo_keyboard_input')

        # Servo Constants
        self.TWIST_TOPIC = "/servo_node/delta_twist_cmds"
        self.JOINT_TOPIC = "/servo_node/delta_joint_cmds"
        self.PLANNING_FRAME_ID = "base_link"
        self.EE_FRAME_ID = "link6"

        # Publishers
        self.twist_pub = self.create_publisher(TwistStamped, self.TWIST_TOPIC, 10)
        self.joint_pub = self.create_publisher(JointJog, self.JOINT_TOPIC, 10)

        # Jazzy Servo ignores input until the command type is set
        self.switch_client = self.create_client(ServoCommandType, "/servo_node/switch_command_type")
        self.command_type = None

        # State Variables
        self.joint_vel_cmd = 1.0
        self.command_frame_id = self.PLANNING_FRAME_ID
        self.joint_names = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]

        self.get_logger().info("Keyboard Servo Node Started (Humble Version)")
        self.print_menu()

    def print_menu(self):
        print("\nReading from keyboard")
        print("---------------------------")
        print(f"Planning Frame: {self.PLANNING_FRAME_ID}")
        print(f"End Effector Frame: {self.EE_FRAME_ID}")
        print("---------------------------")
        print("CONTROLS:")
        print("  Arrow Keys: Move X/Y (Cartesian)")
        print("  '.' / ',':  Move Z Up/Down (Cartesian)")
        print("  1 - 6 keys: Move Joint 1-6")
        print("  'r':        Reverse joint direction")
        print("  'w' / 'e':  Switch Frame (Base / End-Effector)")
        print("  'q':        Quit")

    def set_command_type(self, command_type):
        if self.command_type == command_type:
            return
        if not self.switch_client.wait_for_service(timeout_sec=1.0):
            print("Servo switch_command_type service not available")
            return
        self.switch_client.call_async(ServoCommandType.Request(command_type=command_type))
        self.command_type = command_type

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def run(self):
        while rclpy.ok():

            key = self.get_key()

            twist_msg = TwistStamped()
            joint_msg = JointJog()
            publish_twist = False
            publish_joint = False

            twist_msg.twist.linear.x = 0.0
            twist_msg.twist.linear.y = 0.0
            twist_msg.twist.linear.z = 0.0

            # Set Common Headers
            now = self.get_clock().now().to_msg()

            if key == KeyCode.QUIT:
                break

            # Cartesian Controls (Twist)
            elif key == KeyCode.UP:
                twist_msg.twist.linear.x = 0.5
                publish_twist = True
            elif key == KeyCode.DOWN:
                twist_msg.twist.linear.x = -0.5
                publish_twist = True
            elif key == KeyCode.LEFT:
                twist_msg.twist.linear.y = 0.5
                publish_twist = True
            elif key == KeyCode.RIGHT:
                twist_msg.twist.linear.y = -0.5
                publish_twist = True
            elif key == KeyCode.PERIOD:
                twist_msg.twist.linear.z = -0.5
                publish_twist = True
            elif key == KeyCode.SEMICOLON:
                twist_msg.twist.linear.z = 0.5
                publish_twist = True


            # Joint Jogging
            elif key in [KeyCode.K1, KeyCode.K2, KeyCode.K3, KeyCode.K4, KeyCode.K5, KeyCode.K6]:
                idx = int(key) - 1
                joint_msg.velocities = [0.0] * 6
                joint_msg.velocities[idx] = self.joint_vel_cmd
                publish_joint = True

            elif key == KeyCode.REVERSE:
                self.joint_vel_cmd *= -1.0
                print(f"Joint direction reversed. Velocity: {self.joint_vel_cmd}")

            # Frame Switching
            elif key == KeyCode.FRAME_BASE:
                self.command_frame_id = self.PLANNING_FRAME_ID
                print(f"Command frame set to: {self.command_frame_id}")
            elif key == KeyCode.FRAME_EE:
                self.command_frame_id = self.EE_FRAME_ID
                print(f"Command frame set to: {self.command_frame_id}")
            # else:
            #     twist_msg.twist.linear.x = 0.0
            #     twist_msg.twist.linear.y = 0.0
            #     twist_msg.twist.linear.z = 0.0

            # Publish Logic
            if publish_twist:
                self.set_command_type(ServoCommandType.Request.TWIST)
                twist_msg.header.stamp = now
                twist_msg.header.frame_id = self.command_frame_id
                self.twist_pub.publish(twist_msg)
            elif publish_joint:
                self.set_command_type(ServoCommandType.Request.JOINT_JOG)
                joint_msg.header.stamp = now
                joint_msg.header.frame_id = self.PLANNING_FRAME_ID
                joint_msg.joint_names = self.joint_names
                self.joint_pub.publish(joint_msg)

def main(args=None):
    rclpy.init(args=args)
    node = KeyboardServo()

    # Run spinning in a separate thread so the main loop can block for keyboard input
    spinner = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spinner.start()

    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()