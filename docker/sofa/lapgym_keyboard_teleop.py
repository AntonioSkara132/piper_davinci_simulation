"""Drive a LapGym gripper from the keyboard through twist_socket_bridge:
    grasp-lift-touch (organ, the default) or pick-and-place (rings, with --rings).

Data path:
    teleop_twist_keyboard  --Twist on /robot/cmd_vel-->  twist_socket_bridge
    --UDP 127.0.0.1:5005, {"vel": [vx, vy, vz, wx, wy, wz]}-->  this script (SOFA, Python 3.12)

SOFA runs in its own venv (/opt/sofa_venv) and ROS 2 in the system Python, which is why the
command goes over UDP instead of rclpy.

Key mapping with teleop_twist_keyboard's default layout:
    i / ,        linear.x   -> tilt the gripper forward / back
    j / l        angular.z  -> pan the gripper left / right
    t / b        linear.z   -> push the gripper in / pull it out (depth)
    J / L        linear.y   -> close / open the jaws (shift = holonomic mode)
    k            stop
    r + Enter    (typed in the SOFA pane, not the teleop pane) reset the scene

Mouse in the simulation window:
    scroll                       zoom in / out
    left drag                    rotate the view around its centre
    right drag or shift + left   move the view
    c (window focused)           back to the scene's camera view
The view also changes the image the env uses for its "target visible" reward term.
    q / z        faster / slower (teleop's own speed scaling)

teleop_twist_keyboard only publishes when a key is pressed, so the last command is held until
you press k or another key, the same way robot_controller.RobotController treats it.
The cautery hook is left still.

Usage:
    run_sofa_teleop   (in the piper-jazzy container: starts this script and the ROS nodes)
or alone:
    sofa-python lapgym_keyboard_teleop.py [--rings] [--port 5005] [--no-realtime]
"""

import argparse
import json
import os
import select
import socket
import sys
import time

import numpy as np

from sofa_env.base import RenderFramework, RenderMode
from sofa_env.scenes.grasp_lift_touch.grasp_lift_touch_env import ActionType, GraspLiftTouchEnv, ObservationType
from sofa_env.scenes.pick_and_place.pick_and_place_env import ActionType as PickAndPlaceActionType
from sofa_env.scenes.pick_and_place.pick_and_place_env import ObservationType as PickAndPlaceObservationType
from sofa_env.scenes.pick_and_place.pick_and_place_env import PickAndPlaceEnv

# teleop_twist_keyboard's default speeds. At these speeds a key gives full instrument velocity.
TELEOP_LINEAR_SPEED = 0.5
TELEOP_ANGULAR_SPEED = 1.0

# Index of each gripper degree of freedom in the env's continuous action:
# [pan, tilt, spin, depth, jaw angle] for the gripper; grasp-lift-touch adds 5 values for the cautery hook.
PAN, TILT, SPIN, DEPTH, JAW = range(5)


class WindowedEnvMixin:
    """For a SofaEnv rendered with pygame: a resizable window placed at a chosen screen position, and a
    camera you orbit, move and zoom with the mouse. Put it before the env class: class X(WindowedEnvMixin, SomeEnv)."""

    window_position = (0, 0)
    window_caption = "LapGym"

    def _init_pygame_window(self):
        os.environ["SDL_VIDEO_WINDOW_POS"] = "{},{}".format(*self.window_position)
        self.pygame.init()
        self.pygame.display.set_caption(self.window_caption)
        size = (self._camera_object.widthViewport.value, self._camera_object.heightViewport.value)
        self._window = self.pygame.display.set_mode(size, self.pygame.DOUBLEBUF | self.pygame.OPENGL | self.pygame.RESIZABLE)
        self._init_opengl()

    # Orbit camera state: the point the view rotates around, the distance to it, and the
    # forward / up directions of the view. None until the first frame, then copied from the scene camera.
    orbit = None
    orbit_start = None
    ORBIT_DEFAULT_DISTANCE = 290.0  # mm in front of the scene camera; the view rotates about that point
    ROTATE_RAD_PER_PIXEL = 0.005
    ZOOM_FACTOR_PER_WHEEL_STEP = 0.9

    def _update_rgb_buffer(self) -> np.ndarray:
        # The base class copies into a buffer of the starting size, which fails after a resize.
        self._update_sofa_visuals()
        self._rgb_buffer = self._get_rgb()
        self._flip_window()
        return self._rgb_buffer

    def _init_orbit_from_scene_camera(self) -> None:
        # getOpenGLModelViewMatrix is column-major; its rotation rows are the camera's right, up and -forward axes.
        view = np.array(self._camera_object.getOpenGLModelViewMatrix()).reshape(4, 4).T
        rotation, translation = view[:3, :3], view[:3, 3]
        eye = -rotation.T @ translation
        up = rotation[1]
        forward = -rotation[2]
        self.orbit = {
            "target": eye + forward * self.ORBIT_DEFAULT_DISTANCE,
            "distance": self.ORBIT_DEFAULT_DISTANCE,
            "forward": forward,
            "up": up,
            "world_up": up.copy(),  # left-right dragging rotates about this axis
        }
        self.orbit_start = {key: np.copy(value) for key, value in self.orbit.items()}

    def _update_sofa_visuals(self) -> None:
        """Same as SofaEnv._update_sofa_visuals, but with the orbit camera instead of the scene camera."""
        gl, glu = self.opengl_gl, self.opengl_glu
        if self.orbit is None:
            self._init_orbit_from_scene_camera()
        self.sofa_simulation.updateVisual(self._sofa_root_node)

        # Take the size from the window: env.reset() puts the camera viewport back to its starting size,
        # and the image would then fill only part of the window.
        width, height = self.pygame.display.get_window_size()
        self._camera_object.widthViewport.value = width
        self._camera_object.heightViewport.value = height
        gl.glViewport(0, 0, width, height)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        distance = self.orbit["distance"]
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        # Near and far planes scale with the zoom so close-up views are not clipped.
        glu.gluPerspective(self._camera_object.fieldOfView.value, width / height, max(0.5, 0.02 * distance), 10.0 * distance + 500.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        target = self.orbit["target"]
        eye = target - self.orbit["forward"] * distance
        glu.gluLookAt(*eye, *target, *self.orbit["up"])
        self.sofa_gl.draw(self._sofa_root_node)

    def redraw(self) -> None:
        """Draw the current scene state again, without stepping physics or reading pixels back."""
        self._update_sofa_visuals()
        self._flip_window()

    @staticmethod
    def _rotate(vector: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
        """Rotate vector about a unit axis (Rodrigues' formula)."""
        axis = axis / np.linalg.norm(axis)
        return vector * np.cos(angle) + np.cross(axis, vector) * np.sin(angle) + axis * np.dot(axis, vector) * (1 - np.cos(angle))

    def _orbit_rotate(self, dx: float, dy: float) -> None:
        o = self.orbit
        yaw, pitch = -dx * self.ROTATE_RAD_PER_PIXEL, -dy * self.ROTATE_RAD_PER_PIXEL
        o["forward"] = self._rotate(o["forward"], o["world_up"], yaw)
        o["up"] = self._rotate(o["up"], o["world_up"], yaw)
        right = np.cross(o["forward"], o["up"])
        o["forward"] = self._rotate(o["forward"], right, pitch)
        o["up"] = self._rotate(o["up"], right, pitch)

    def _orbit_pan(self, dx: float, dy: float) -> None:
        o = self.orbit
        right = np.cross(o["forward"], o["up"])
        # Scale so the point under the cursor roughly follows the mouse.
        mm_per_pixel = 2.0 * o["distance"] * np.tan(np.deg2rad(self._camera_object.fieldOfView.value) / 2) / self._camera_object.heightViewport.value
        o["target"] = o["target"] - right * dx * mm_per_pixel + o["up"] * dy * mm_per_pixel

    def handle_window_events(self) -> tuple:
        """Process window events. Returns (window_still_open, view_changed)."""
        pygame = self.pygame
        view_changed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, view_changed
            if event.type == pygame.VIDEORESIZE:
                # The camera viewport sets the GL viewport and the aspect ratio, so the image follows the window.
                self._camera_object.widthViewport.value = max(event.w, 64)
                self._camera_object.heightViewport.value = max(event.h, 64)
                view_changed = True
            elif self.orbit is None:
                continue
            elif event.type == pygame.MOUSEWHEEL:
                self.orbit["distance"] = float(np.clip(self.orbit["distance"] * self.ZOOM_FACTOR_PER_WHEEL_STEP ** event.y, 5.0, 3000.0))
                view_changed = True
            elif event.type == pygame.MOUSEMOTION and any(event.buttons):
                dx, dy = event.rel
                shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                if event.buttons[0] and not shift:
                    self._orbit_rotate(dx, dy)
                else:  # right or middle button, or shift + left button
                    self._orbit_pan(dx, dy)
                view_changed = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                self.orbit = {key: np.copy(value) for key, value in self.orbit_start.items()}
                view_changed = True
        return True, view_changed


class WindowedGraspLiftTouchEnv(WindowedEnvMixin, GraspLiftTouchEnv):
    """GraspLiftTouchEnv in a resizable window with a mouse-controlled camera."""

    window_caption = "LapGym grasp-lift-touch"
    ORBIT_DEFAULT_DISTANCE = 290.0  # mm; the liver is about this far in front of the scene camera


class WindowedPickAndPlaceEnv(WindowedEnvMixin, PickAndPlaceEnv):
    """PickAndPlaceEnv in a resizable window with a mouse-controlled camera."""

    window_caption = "LapGym pick-and-place"
    ORBIT_DEFAULT_DISTANCE = 220.0  # the scene camera is about 220 mm from the board centre


# The scene starts the gripper at about 130 mm depth, where it sits at or past the top edge of
# the camera image. At 190 mm its jaws are in view above the liver.
START_DEPTH = 190.0

# Shortest time between redraws for mouse camera moves done between physics steps (about 60 frames per second).
REDRAW_PERIOD = 1.0 / 60.0


def reset_env(env) -> None:
    """Reset the scene and, in grasp-lift-touch, push the gripper in far enough to be visible."""
    env.reset()
    if not isinstance(env, GraspLiftTouchEnv):
        return
    state = env.gripper.articulated_state.copy()
    state[DEPTH] = max(state[DEPTH], START_DEPTH)
    env.gripper.set_articulated_state(state)


def read_console_key() -> str:
    """Return a line typed in this script's terminal pane, or "" if nothing was typed."""
    if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.readline().strip().lower()
    return ""


def twist_to_action(vel: np.ndarray, size: int) -> np.ndarray:
    """Map [vx, vy, vz, wx, wy, wz] from the bridge to the env's action in [-1, 1] (size values)."""
    action = np.zeros(size, dtype=np.float32)
    action[TILT] = vel[0] / TELEOP_LINEAR_SPEED
    action[JAW] = -vel[1] / TELEOP_LINEAR_SPEED  # J (+y) closes, L (-y) opens
    action[DEPTH] = vel[2] / TELEOP_LINEAR_SPEED
    action[PAN] = vel[5] / TELEOP_ANGULAR_SPEED
    return np.clip(action, -1.0, 1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rings", action="store_true", help="pick-and-place (rings) instead of grasp-lift-touch (organ)")
    parser.add_argument("--port", type=int, default=5005, help="UDP port twist_socket_bridge sends to")
    parser.add_argument("--no-realtime", action="store_true", help="step as fast as possible instead of at wall-clock speed")
    parser.add_argument("--headless", action="store_true", help="render off-screen without a window (for testing)")
    parser.add_argument("--width", type=int, default=950, help="starting window width in pixels")
    parser.add_argument("--height", type=int, default=1080, help="starting window height in pixels")
    parser.add_argument("--x", type=int, default=0, help="window x position on screen")
    parser.add_argument("--y", type=int, default=40, help="window y position on screen")
    parser.add_argument("--speed", type=float, default=2.0, help="multiplier on the env's default instrument speeds")
    parser.add_argument("--dt", type=float, default=0.05, help="simulated seconds per step (also the window update period)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", args.port))
    sock.setblocking(False)

    common = dict(
        render_mode=RenderMode.HEADLESS if args.headless else RenderMode.HUMAN,
        render_framework=RenderFramework.PYGLET if args.headless else RenderFramework.PYGAME,
        image_shape=(args.width, args.height),  # the scene reads this as (width, height)
        time_step=args.dt,
        frame_skip=1,
        # grasp-lift-touch's default speeds: [pan 15 deg/s, tilt 15 deg/s, spin 25 deg/s, depth 25 mm/s, jaw 20 deg/s].
        maximum_state_velocity=args.speed * np.array([15.0, 15.0, 25.0, 25.0, 20.0]),
    )
    if args.rings:
        WindowedPickAndPlaceEnv.window_position = (args.x, args.y)
        env = WindowedPickAndPlaceEnv(
            observation_type=PickAndPlaceObservationType.STATE,
            action_type=PickAndPlaceActionType.CONTINUOUS,
            num_active_pegs=3,
            randomize_color=True,
            start_grasped=False,
            **common,
        )
    else:
        WindowedGraspLiftTouchEnv.window_position = (args.x, args.y)
        env = WindowedGraspLiftTouchEnv(observation_type=ObservationType.STATE, action_type=ActionType.CONTINUOUS, **common)
    action_size = env.action_space.shape[0]
    reset_env(env)
    sim_dt = env.time_step * env.frame_skip
    print(f"Listening for twist commands on UDP 127.0.0.1:{args.port}. Simulation step {sim_dt:.3f} s.", flush=True)
    print("Type r + Enter here to reset the scene.", flush=True)

    vel = np.zeros(6)
    last_print = time.monotonic()
    steps_since_print = 0
    next_step_time = time.monotonic()
    try:
        while True:
            # Read every message that arrived since the last step and keep the newest.
            try:
                while True:
                    data, _ = sock.recvfrom(4096)
                    msg = json.loads(data.decode())
                    if "vel" in msg:
                        vel = np.asarray(msg["vel"], dtype=float)[:6]
            except BlockingIOError:
                pass

            if not args.headless and not env.handle_window_events()[0]:
                break

            if read_console_key() == "r":
                print("Resetting.", flush=True)
                reset_env(env)
                vel[:] = 0.0

            _, _, terminated, truncated, info = env.step(twist_to_action(vel, action_size))
            if terminated or truncated:
                print("Episode finished, resetting.", flush=True)
                reset_env(env)
                vel[:] = 0.0

            steps_since_print += 1
            now = time.monotonic()
            if now - last_print >= 5.0:
                rate = steps_since_print * sim_dt / (now - last_print)
                phase = getattr(env, "active_phase", None)
                print(f"real-time factor {rate:.2f}  phase {phase.name if phase is not None else '-'}  gripper [pan tilt spin depth jaw] {np.round(env.gripper.articulated_state, 1).tolist()}  command {np.round(vel, 2).tolist()}", flush=True)
                last_print, steps_since_print = now, 0

            # Wait until wall-clock time catches up with simulated time.
            if not args.no_realtime:
                next_step_time += sim_dt
                if time.monotonic() > next_step_time:
                    next_step_time = time.monotonic()  # running behind: do not try to catch up
                # Use the spare time until the next physics step to follow the mouse:
                # redraw only when the view changed, at most every REDRAW_PERIOD seconds.
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
    # SOFA's Python bindings segfault during interpreter shutdown (Py_FinalizeEx), after the
    # scene is already closed. Exit without running that cleanup.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
