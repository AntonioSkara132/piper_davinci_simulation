"""Da Vinci instrument on the AgileX Piper, driving a LapGym scene:
    --scene organ   grasp-lift-touch: grasp the gallbladder and lift it (default)
    --scene rings   pick-and-place: pick up the ring and put it on a peg of its colour

The instrument's position and orientation come from the Piper: its joint sliders in RViz (or the
real arm's joint states) -> robot_state_publisher -> TF base_link -> instrument_wrist ->
piper_tool_bridge -> UDP {"tool_pose": [...]} -> this script.

The degrees of freedom the da Vinci adaptor drives on the instrument come from the keyboard:
teleop_twist_keyboard -> twist_socket_bridge -> UDP {"vel": [...]} -> this script.

    j / l        roll the instrument about its shaft
    i / ,        wrist pitch
    t / b        wrist yaw (both jaws turn together)
    J / L        close / open the jaws (shift = holonomic mode)
    k            stop
In this script's terminal pane:
    a + Enter    re-anchor: keep the instrument where it is in the scene and take the Piper's
                 current pose as the new reference (like the clutch pedal on a da Vinci console)
    r + Enter    reset the scene and re-anchor at the start position

Placement: the Piper base is not fixed in the scene. When the first pose arrives (and on a + Enter
or r + Enter), the base is placed so that the instrument wrist is where the scene's gripper starts,
with the Piper base standing upright (its z axis against the scene's gravity) and turned so the
shaft points the same way horizontally. After that, Piper motion moves the instrument one to one
(times --motion-scale). There is no trocar constraint: the shaft moves freely.

Mouse in the simulation window: scroll to zoom, left drag to rotate, right drag to move, c to reset the view.
"""

import argparse
import json
import os
import socket
import sys
import time

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from sofa_env.base import RenderFramework, RenderMode
from sofa_env.scenes.grasp_lift_touch.grasp_lift_touch_env import ActionType, ObservationType
from sofa_env.scenes.pick_and_place.pick_and_place_env import ActionType as PickAndPlaceActionType
from sofa_env.scenes.pick_and_place.pick_and_place_env import ObservationType as PickAndPlaceObservationType
from sofa_env.scenes.pick_and_place.pick_and_place_env import PickAndPlaceEnv

from lapgym_keyboard_teleop import REDRAW_PERIOD, TELEOP_ANGULAR_SPEED, TELEOP_LINEAR_SPEED, WindowedEnvMixin, WindowedGraspLiftTouchEnv, read_console_key, reset_env

# Key rates at teleop_twist_keyboard's default speeds (degrees per second).
ROLL_RATE = 90.0
WRIST_RATE = 60.0
YAW_RATE = 60.0
GRIP_RATE = 40.0
# Half the angle between the jaws, and how far each jaw may turn (degrees).
GRIP_MAX = 35.0
JAW_MAX = 80.0
WRIST_MAX = 80.0


class WindowedPickAndPlaceEnv(WindowedEnvMixin, PickAndPlaceEnv):
    window_caption = "LapGym pick-and-place"
    ORBIT_DEFAULT_DISTANCE = 220.0  # the scene camera is about 220 mm from the board centre


class PiperRegistration:
    """Places the Piper base in the scene and maps instrument poses from the base frame (metres) to the scene (millimetres)."""

    def __init__(self, scene_up: np.ndarray, motion_scale: float) -> None:
        self.scene_up = scene_up / np.linalg.norm(scene_up)
        self.motion_scale = motion_scale
        self.rotation = None  # scene <- base
        self.translation = None

    def anchor(self, base_pose: np.ndarray, scene_position: np.ndarray, scene_rotation: Rotation) -> None:
        """Place the base so that base_pose ([x y z qx qy qz qw], metres) lands on the given scene pose."""
        # Upright base: base z along scene up. Pick any base x perpendicular to it, then turn about up.
        z = self.scene_up
        x = np.cross([1.0, 0.0, 0.0] if abs(z[0]) < 0.9 else [0.0, 0.0, 1.0], z)
        x /= np.linalg.norm(x)
        upright = Rotation.from_matrix(np.column_stack([x, np.cross(z, x), z]))

        # Turn about up so the shaft's horizontal direction matches the scene instrument's.
        shaft_in_base = Rotation.from_quat(base_pose[3:]).apply([0.0, 0.0, 1.0])
        shaft_upright = upright.apply(shaft_in_base)
        shaft_scene = scene_rotation.apply([0.0, 0.0, 1.0])
        flat = lambda v: v - z * np.dot(v, z)
        a, b = flat(shaft_upright), flat(shaft_scene)
        yaw = 0.0
        if np.linalg.norm(a) > 1e-6 and np.linalg.norm(b) > 1e-6:
            yaw = np.arctan2(np.dot(np.cross(a, b), z), np.dot(a, b))
        self.rotation = Rotation.from_rotvec(z * yaw) * upright
        self.translation = scene_position - self.rotation.apply(base_pose[:3] * 1000.0 * self.motion_scale)

    def to_scene(self, base_pose: np.ndarray) -> tuple:
        position = self.translation + self.rotation.apply(base_pose[:3] * 1000.0 * self.motion_scale)
        rotation = self.rotation * Rotation.from_quat(base_pose[3:])
        return position, rotation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scene", choices=["organ", "rings"], default="organ", help="organ: grasp-lift-touch, rings: pick-and-place")
    parser.add_argument("--port", type=int, default=5005, help="UDP port the two bridges send to")
    parser.add_argument("--no-realtime", action="store_true", help="step as fast as possible instead of at wall-clock speed")
    parser.add_argument("--headless", action="store_true", help="render off-screen without a window (for testing)")
    parser.add_argument("--width", type=int, default=950, help="starting window width in pixels")
    parser.add_argument("--height", type=int, default=1080, help="starting window height in pixels")
    parser.add_argument("--x", type=int, default=0, help="window x position on screen")
    parser.add_argument("--y", type=int, default=40, help="window y position on screen")
    parser.add_argument("--dt", type=float, default=0.05, help="simulated seconds per step")
    parser.add_argument("--motion-scale", type=float, default=1.0, help="instrument motion in the scene per Piper motion (0.5 = half)")
    parser.add_argument("--max-speed", type=float, default=300.0, help="fastest instrument motion in the scene, mm/s (fast slider moves are smoothed)")
    parser.add_argument("--max-turn-rate", type=float, default=180.0, help="fastest instrument rotation, deg/s")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", args.port))
    sock.setblocking(False)

    common = dict(
        render_mode=RenderMode.HEADLESS if args.headless else RenderMode.HUMAN,
        render_framework=RenderFramework.PYGLET if args.headless else RenderFramework.PYGAME,
        image_shape=(args.width, args.height),
        time_step=args.dt,
        frame_skip=1,
    )
    if args.scene == "organ":
        WindowedGraspLiftTouchEnv.window_position = (args.x, args.y)
        env = WindowedGraspLiftTouchEnv(
            observation_type=ObservationType.STATE,
            action_type=ActionType.CONTINUOUS,
            create_scene_kwargs={"instrument_wrist": True, "double_action_gripper": True},
            **common,
        )
    else:
        WindowedPickAndPlaceEnv.window_position = (args.x, args.y)
        env = WindowedPickAndPlaceEnv(
            observation_type=PickAndPlaceObservationType.STATE,
            action_type=PickAndPlaceActionType.CONTINUOUS,
            create_scene_kwargs={"instrument_wrist": True, "gripper_randomization": {}},
            num_active_pegs=3,
            randomize_color=True,
            start_grasped=False,
            **common,
        )
        # The env's action sets the instrument's trocar state and one jaw angle, which would move the
        # instrument back to its trocar pose and make the jaws symmetric again on every step.
        env._do_action = lambda action: None
    sim_dt = env.time_step * env.frame_skip
    no_action = np.zeros(env.action_space.shape, dtype=np.float32)

    def reset_scene() -> None:
        if args.scene == "rings":
            env.reset()
            return
        # Put the instrument's own set_state back first: the reset places it with that method.
        try:
            del env.gripper.set_state
        except AttributeError:
            pass
        reset_env(env)
        # The Piper sets the instrument pose directly. Stop the env's pan/tilt/spin/depth state from
        # moving it back to the trocar-based pose on every step.
        env.gripper.set_state = lambda state: None

    reset_scene()
    gravity = np.array(env._sofa_root_node.gravity.value, dtype=float)
    registration = PiperRegistration(scene_up=-gravity, motion_scale=args.motion_scale)

    def instrument_pose() -> tuple:
        pose = np.array(env.gripper.get_pose(), dtype=float)
        return pose[:3].copy(), Rotation.from_quat(pose[3:])

    # Pose command sent to SOFA, moved toward the Piper target at a limited speed.
    command_position, command_rotation = instrument_pose()
    roll = wrist = yaw = 0.0
    grip = 20.0

    print(f"Listening on UDP 127.0.0.1:{args.port} for the Piper pose and the keyboard. Simulation step {sim_dt:.3f} s.", flush=True)
    print("Type a + Enter here to re-anchor, r + Enter to reset the scene.", flush=True)

    vel = np.zeros(6)
    tool_pose = None
    tool_pose_time = 0.0
    anchor_pending = True
    last_print = time.monotonic()
    steps_since_print = 0
    next_step_time = time.monotonic()
    try:
        while True:
            try:
                while True:
                    data, _ = sock.recvfrom(4096)
                    msg = json.loads(data.decode())
                    if "vel" in msg:
                        vel = np.asarray(msg["vel"], dtype=float)[:6]
                    if "tool_pose" in msg:
                        tool_pose = np.asarray(msg["tool_pose"], dtype=float)
                        tool_pose_time = time.monotonic()
            except BlockingIOError:
                pass

            if not args.headless and not env.handle_window_events()[0]:
                break

            key = read_console_key()
            if key == "r":
                print("Resetting the scene.", flush=True)
                reset_scene()
                command_position, command_rotation = instrument_pose()
                roll = wrist = yaw = 0.0
                grip = 20.0
                vel[:] = 0.0
                anchor_pending = True
            elif key == "a":
                anchor_pending = True

            if tool_pose is not None and anchor_pending:
                # The anchored instrument frame is the command without the keyboard roll.
                registration.anchor(tool_pose, command_position, command_rotation * Rotation.from_euler("z", -roll, degrees=True))
                anchor_pending = False
                print(f"Anchored the Piper to the scene. Base at {np.round(registration.translation, 1).tolist()} mm.", flush=True)

            # Keyboard: roll, wrist pitch, wrist yaw and grip.
            roll += vel[5] / TELEOP_ANGULAR_SPEED * ROLL_RATE * sim_dt
            wrist = float(np.clip(wrist + vel[0] / TELEOP_LINEAR_SPEED * WRIST_RATE * sim_dt, -WRIST_MAX, WRIST_MAX))
            new_grip = float(np.clip(grip - vel[1] / TELEOP_LINEAR_SPEED * GRIP_RATE * sim_dt, 0.0, GRIP_MAX))  # J (+y) closes
            # Once something is grasped, the jaws do not close further, only open (as in the env's own jaw control).
            grip = max(new_grip, grip) if env.gripper.grasp_established else new_grip
            yaw = float(np.clip(yaw + vel[2] / TELEOP_LINEAR_SPEED * YAW_RATE * sim_dt, -(JAW_MAX - grip), JAW_MAX - grip))
            env.gripper.set_wrist_angle(wrist)
            env.gripper.set_jaw_angles(yaw + grip, yaw - grip)

            # Piper: move the instrument toward its pose, no faster than --max-speed / --max-turn-rate.
            if registration.rotation is not None:
                target_position, target_rotation = registration.to_scene(tool_pose)
                target_rotation = target_rotation * Rotation.from_euler("z", roll, degrees=True)
                step = target_position - command_position
                max_step = args.max_speed * sim_dt
                if np.linalg.norm(step) > max_step:
                    step *= max_step / np.linalg.norm(step)
                command_position = command_position + step
                turn = np.degrees((command_rotation.inv() * target_rotation).magnitude())
                fraction = 1.0 if turn < 1e-6 else min(1.0, args.max_turn_rate * sim_dt / turn)
                command_rotation = Slerp([0.0, 1.0], Rotation.concatenate([command_rotation, target_rotation]))(fraction)
                env.gripper.set_pose(np.concatenate([command_position, command_rotation.as_quat()]))

            _, _, terminated, truncated, _ = env.step(no_action)
            if terminated or truncated:
                print("Episode finished. Type r + Enter to start again.", flush=True)

            steps_since_print += 1
            now = time.monotonic()
            if now - last_print >= 5.0:
                rate = steps_since_print * sim_dt / (now - last_print)
                piper = "no Piper pose yet" if tool_pose is None else f"Piper pose {now - tool_pose_time:.1f} s old"
                grasped = "grasped" if env.gripper.grasp_established else "not grasped"
                phase = getattr(env, "active_phase", None)
                print(
                    f"real-time factor {rate:.2f}  phase {phase.name if phase is not None else '-'}  {piper}  wrist at {np.round(command_position, 1).tolist()} mm"
                    f"  roll {roll:.0f}  pitch {wrist:.0f}  yaw {yaw:.0f}  grip {grip:.0f}  {grasped}",
                    flush=True,
                )
                last_print, steps_since_print = now, 0

            if not args.no_realtime:
                next_step_time += sim_dt
                if time.monotonic() > next_step_time:
                    next_step_time = time.monotonic()
                window_open = True
                while window_open and time.monotonic() < next_step_time:
                    if not args.headless:
                        window_open, view_changed = env.handle_window_events()
                        if view_changed:
                            env.redraw()
                    time.sleep(min(REDRAW_PERIOD, max(0.0, next_step_time - time.monotonic())))
                if not window_open:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        env.close()
        sock.close()


if __name__ == "__main__":
    main()
    # SOFA's Python bindings segfault during interpreter shutdown (Py_FinalizeEx). Exit without that cleanup.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
