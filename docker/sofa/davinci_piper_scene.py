"""Da Vinci instrument on the AgileX Piper, driving a LapGym scene:
    --scene organ   grasp-lift-touch: grasp the gallbladder and lift it (default)
    --scene rings   pick-and-place: pick up the ring and put it on a peg of its colour

Everything the instrument does comes from TF: the Piper and adaptor joint states ->
robot_state_publisher -> TF -> piper_tool_bridge -> UDP -> this script. Each message is

    {"tool_pose": [x, y, z, qx, qy, qz, qw], "pitch": deg, "jaws": [jaw_1 deg, jaw_2 deg]}

tool_pose is the frame instrument_wrist in the Piper base frame (metres): the wrist at the end of
the shaft, with the shaft roll. pitch is the wrist joint, jaws the two jaw joints.

The Piper base stands at a fixed place in each scene (BASES below, or --base): with the arm in the
slider start pose, the instrument is where the scene's own gripper starts. Piper motion moves the
instrument one to one. There is no trocar constraint: the shaft moves freely.

In this script's terminal:
    r + Enter    reset the scene

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

from lapgym_keyboard_teleop import REDRAW_PERIOD, WindowedGraspLiftTouchEnv, WindowedPickAndPlaceEnv, read_console_key, reset_env

# Piper base in each scene: position (mm) and orientation (quaternion x y z w, scene <- base). The
# base stands upright (its z axis against the scene's gravity), turned so that the slider start pose
# puts the instrument on the scene's start pose, shaft pointing the same way horizontally.
BASES = {
    "organ": ([-461.607, -21.706, -354.057], [0.660117, -0.253466, 0.253466, 0.660117]),
    "rings": ([39.39, 17.047, -461.686], [0.5, 0.5, 0.5, -0.5]),
}
# Jaw limits of the SOFA instrument (degrees): half the angle between the jaws, and each jaw's turn.
GRIP_MAX = 35.0
JAW_MAX = 80.0


class FixedStartGraspLiftTouchEnv(WindowedGraspLiftTouchEnv):
    """Grasp-lift-touch with the gripper starting at the same pose on every reset (the scene adds random noise)."""

    def _init_sim(self) -> None:
        super()._init_sim()
        self.gripper.ptsd_reset_noise = None
        self.gripper.angle_reset_noise = None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scene", choices=["organ", "rings"], default="organ", help="organ: grasp-lift-touch, rings: pick-and-place")
    parser.add_argument("--port", type=int, default=5006, help="UDP port piper_tool_bridge sends to")
    parser.add_argument("--base", type=float, nargs=7, metavar=("X", "Y", "Z", "QX", "QY", "QZ", "QW"), help="Piper base in the scene (mm, quaternion), instead of the scene's default")
    parser.add_argument("--no-realtime", action="store_true", help="step as fast as possible instead of at wall-clock speed")
    parser.add_argument("--headless", action="store_true", help="render off-screen without a window (for testing)")
    parser.add_argument("--width", type=int, default=950, help="starting window width in pixels")
    parser.add_argument("--height", type=int, default=1080, help="starting window height in pixels")
    parser.add_argument("--x", type=int, default=0, help="window x position on screen")
    parser.add_argument("--y", type=int, default=40, help="window y position on screen")
    parser.add_argument("--dt", type=float, default=0.05, help="simulated seconds per step")
    parser.add_argument("--max-speed", type=float, default=300.0, help="fastest instrument motion in the scene, mm/s (fast slider moves are smoothed)")
    parser.add_argument("--max-turn-rate", type=float, default=180.0, help="fastest instrument rotation, deg/s")
    args = parser.parse_args()

    base_position, base_quat = (args.base[:3], args.base[3:]) if args.base else BASES[args.scene]
    base_position, base_rotation = np.array(base_position, dtype=float), Rotation.from_quat(base_quat)

    def to_scene(tool_pose: np.ndarray) -> tuple:
        """instrument_wrist in the Piper base frame (metres) -> position (mm) and rotation in the scene."""
        return base_position + base_rotation.apply(tool_pose[:3] * 1000.0), base_rotation * Rotation.from_quat(tool_pose[3:])

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
        FixedStartGraspLiftTouchEnv.window_position = (args.x, args.y)
        env = FixedStartGraspLiftTouchEnv(
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

    def instrument_pose() -> tuple:
        pose = np.array(env.gripper.get_pose(), dtype=float)
        return pose[:3].copy(), Rotation.from_quat(pose[3:])

    reset_scene()
    # Pose command sent to SOFA, moved toward the Piper's pose at a limited speed.
    command_position, command_rotation = instrument_pose()
    grip = 20.0

    print(f"Listening on UDP 127.0.0.1:{args.port} for the instrument frames. Simulation step {sim_dt:.3f} s.", flush=True)
    print(f"Piper base at {np.round(base_position, 1).tolist()} mm. Type r + Enter here to reset the scene.", flush=True)

    message = None
    message_time = 0.0
    last_print = time.monotonic()
    steps_since_print = 0
    next_step_time = time.monotonic()
    try:
        while True:
            try:
                while True:
                    data, _ = sock.recvfrom(4096)
                    message = json.loads(data.decode())
                    message_time = time.monotonic()
            except BlockingIOError:
                pass

            if not args.headless and not env.handle_window_events()[0]:
                break

            if read_console_key() == "r":
                print("Resetting the scene.", flush=True)
                reset_scene()
                command_position, command_rotation = instrument_pose()
                grip = 20.0

            if message is not None:
                # Wrist and jaws. Their mean turns both jaws (yaw), half their difference opens them (grip).
                env.gripper.set_wrist_angle(message["pitch"])
                jaw_1, jaw_2 = message["jaws"]
                yaw = (jaw_1 + jaw_2) / 2.0
                new_grip = float(np.clip((jaw_1 - jaw_2) / 2.0, 0.0, GRIP_MAX))
                # Once something is grasped, the jaws do not close further, only open (as in the env's own jaw control).
                grip = max(new_grip, grip) if env.gripper.grasp_established else new_grip
                yaw = float(np.clip(yaw, -(JAW_MAX - grip), JAW_MAX - grip))
                env.gripper.set_jaw_angles(yaw + grip, yaw - grip)

                # Instrument pose: move toward the Piper's, no faster than --max-speed / --max-turn-rate.
                target_position, target_rotation = to_scene(np.asarray(message["tool_pose"], dtype=float))
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
                frames = "no instrument frames yet" if message is None else f"frames {now - message_time:.1f} s old"
                grasped = "grasped" if env.gripper.grasp_established else "not grasped"
                phase = getattr(env, "active_phase", None)
                angles = "" if message is None else f"  pitch {message['pitch']:.0f}  jaws {message['jaws'][0]:.0f} {message['jaws'][1]:.0f}"
                print(
                    f"real-time factor {rate:.2f}  phase {phase.name if phase is not None else '-'}  {frames}  wrist at {np.round(command_position, 1).tolist()} mm"
                    f"{angles}  {grasped}",
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
