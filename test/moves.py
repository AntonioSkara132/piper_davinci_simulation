"""Publish the same Twist messages as the ARM / INSTRUMENT keys, with exact durations."""
import sys
import time

import rclpy
from geometry_msgs.msg import Twist

rclpy.init()
node = rclpy.create_node("test_moves")
arm = node.create_publisher(Twist, "/piper/cmd_vel", 10)
tool = node.create_publisher(Twist, "/davinci/cmd_vel", 10)


def move(pub, seconds, x=0.0, y=0.0, z=0.0, wz=0.0, pause=0.4):
    msg = Twist()
    msg.linear.x, msg.linear.y, msg.linear.z, msg.angular.z = x, y, z, wz
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pub.publish(msg)
        time.sleep(0.01)
    pub.publish(Twist())
    time.sleep(pause)


time.sleep(1.0)
what = sys.argv[1]
if what == "grasp":
    move(arm, 26 / 40, y=0.5)
    move(arm, 24.7 / 40, x=-0.5)
    move(arm, 40.7 / 40, z=-0.5)
    move(tool, 3.0, y=0.5, pause=0.8)
elif what == "lift":
    move(arm, 1.0, z=0.5)
elif what == "down":
    move(arm, 1.0, z=-0.5)
elif what == "up_short":
    move(arm, 0.5, z=0.5)
