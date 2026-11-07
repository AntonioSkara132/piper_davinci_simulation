Click in the upper right corner for Table of Contents ↗️

# Piper da Vinci Simulation
Welcome! These instructions will help you set up everything needed to control a da Vinci surgical instrument held by an AgileX Piper robot arm, first in simulation and later on the real arm.

> [!NOTE]
> If you encounter an error or a problem during installation, first check out the [Issues](../../issues) tab; maybe the problem has already been solved. If not, create a new issue.

## Intro
The robot is an **AgileX Piper**, a small 6-joint arm[^1]. On its flange sits an **open-platform adaptor for da Vinci Si instruments**[^2], which holds an 8 mm da Vinci Si instrument (EndoWrist). The adaptor's motors turn the four input discs of the instrument, and these move:

- the **roll** of the instrument about its shaft,
- the **wrist pitch**,
- **each jaw separately**. Turning both jaws the same way is wrist yaw; turning them apart opens and closes the grip.

The arm decides where the instrument is and which way its shaft points. The adaptor decides what the instrument's tip does.

The simulation has two parts:

- **ROS 2 Jazzy** with AgileX's official driver [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2). RViz shows the Piper with the adaptor and the instrument.
- **SOFA v25.12** with two surgical training scenes from [LapGym](https://github.com/ScheiklP/sofa_env)[^3]:
  - **rings** (pick_and_place): pick up a ring and put it on a peg of the same colour,
  - **organ** (grasp_lift_touch): grasp the gallbladder and lift it.

  The instrument in these scenes has the same degrees of freedom as the adaptor: roll, wrist pitch and two independent jaws.

You control everything with two keyboards in one terminal: the **ARM keys** move the instrument tip through the Piper, and the **INSTRUMENT keys** drive the adaptor. This is how the pieces are connected:

```
ARM keys ──/piper/cmd_vel──> piper_cartesian_jog ──control/joint_states──> robot_state_publisher ──TF──> piper_tool_bridge ──UDP──> SOFA
                             (inverse kinematics)                          (RViz shows the arm)          (pose of the instrument)

INSTRUMENT keys ──/davinci/cmd_vel──> twist_socket_bridge ──UDP──> SOFA (roll, wrist pitch, wrist yaw, grip)
```

SOFA runs in its own Python environment, so it talks to ROS through UDP messages on the same computer (port 5006) instead of ROS topics. On the real arm, the AgileX driver reads the same `control/joint_states` topic and moves the arm to those joint positions.

> [!IMPORTANT]
> Everything in this repository has been tested in simulation only. Driving the real Piper with these programs has not been tested yet. Read the [Real arm](#real-arm) section before you try.

## Reporting problems
If you encounter an error that you can't solve yourself or get stuck on some step, please open an [Issue](../../issues) in this repository. Specify your operating system and method of installation, describe your problem, and include the entire output of the command that resulted in the error. This is the quickest way to get help, and it helps other students who run into the same error later.

## Installation
Everything runs in a **Docker container**: ROS 2 Jazzy needs Ubuntu 24.04, and SOFA and LapGym need a specific set of Python packages. The Docker image contains all of it, so everyone gets the same setup from one build command.

### Docker installation
Very briefly, Docker is a tool that packs everything needed for a specific application into one container. You can look at it as a lightweight virtual machine running on your computer. If you want to learn more, take a look at the [official website](https://www.docker.com/). Detailed step-by-step instructions are given below.

#### Prerequisites
- Linux with a desktop (X11 or Wayland). Tested on Ubuntu 22.04 with GNOME on Wayland.
- About 12 GB of free disk space. The image is about 9 GB.
- Graphics: tested with AMD integrated graphics, which the container uses through `/dev/dri`. Intel graphics work the same way. NVIDIA graphics have not been tested; they need the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) and extra `docker run` options.

#### Step-by-step instructions
Follow these [instructions](https://docs.docker.com/engine/install/ubuntu/) to install the Docker engine.

Then follow these [optional steps](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) to manage Docker as a non-root user. If you skip this, every `docker` command will have to be run with `sudo`.

Clone this repository into your home or any other directory, and go to the `docker` folder:
```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
```

Build the Docker image. You will see a lot of output. The first build downloads several GB (ROS 2, SOFA, Python packages), so it takes a while. Wait until it's done.
```bash
docker build -t piper-jazzy .
```

Once you have an image, you need a container. The `run_piper.sh` script creates it the first time and opens a shell in it:
```bash
./run_piper.sh
```

When the script finishes, your terminal prompt changes from
```bash
<your username>@<your hostname>
```
to
```bash
root@<your hostname>
```
This means you are now "inside" the container. ROS 2 and the Piper driver are already loaded in every shell.

> [!TIP]
> Short reminder on commands for working with the container:
> - Exit from the container shell - press `Ctrl+d`. The container keeps running in the background.
> - Open another terminal in the same container - run `./run_piper.sh` again in a new terminal window.
> - Run one command in the container from your own terminal - `./run_piper.sh <command>`
> - Stop the container - `docker stop piper-jazzy`
> - Start over from the clean image (deletes everything you changed inside the container) - `docker rm -f piper-jazzy`
> - After rebuilding the image - `docker rm -f piper-jazzy`, then `./run_piper.sh`, so the container is made from the new image.

What `run_piper.sh` does:

| Option | Why |
|---|---|
| `xhost +local:` | lets the container open windows on your desktop |
| `--net=host` | ROS 2 topics are visible on your computer, and the container can use the CAN interface of the real arm |
| `--privileged` | needed to bring the CAN interface up from inside the container |
| `DISPLAY`, `/tmp/.X11-unix` | RViz and SOFA windows open on your desktop |
| `--device /dev/dri` | hardware OpenGL for RViz and SOFA |

> [!WARNING]
> `xhost +local:` allows every local user's programs to draw on your display until you log out. On a shared computer, undo it with `xhost -local:` when you are done.
>
> Because of `--net=host`, everyone on the same network with the same `ROS_DOMAIN_ID` sees each other's ROS topics. In a lab with several students, give each computer its own number, for example `export ROS_DOMAIN_ID=17` (any number from 0 to 101).

Build options, added to the `docker build` command:

| Option | Effect |
|---|---|
| `--build-arg WITH_SOFA=false` | leaves out SOFA and the simulation (about 3 GB smaller) |
| `--build-arg WITH_MOVEIT=true` | also installs MoveIt and builds `agx_arm_moveit` (a few GB larger) |
| `--build-arg AGX_ARM_ROS_REF=ros2 --build-arg PYAGXARM_REF=main` | newest Piper driver and SDK instead of the tested versions |

### Without Docker
Only the Docker setup is tested and supported. If you have Ubuntu 24.04 with ROS 2 Jazzy and want to install natively, the [Dockerfile](docker/Dockerfile) lists every step in order. The scripts expect the same paths as in the image: `/opt/sofa`, `/opt/sofa_venv`, `/opt/sofa_env`, `/opt/sofa_teleop` and `/root/davinci_piper`.

## Testing your setup with an example
Start the ring scene. Inside the container:
```bash
run_davinci_piper --rings
```
or from your own terminal, in the `docker` folder:
```bash
./run_piper.sh run_davinci_piper --rings
```

After a few seconds, three windows open and fill the screen:

```
+--------------+------------------+
|              |      RViz        |
|     SOFA     |  (Piper + tool)  |
|  ring scene  +------------------+
|              |  keys terminal   |
+--------------+------------------+
```

The **keys terminal** has three panes. Click on a pane to type in it:

1. **SOFA** - messages from the simulation. Every 5 seconds it prints a status line with the position of the instrument wrist (in millimetres), the roll, pitch, yaw and grip angles, and whether something is grasped.
2. **ARM keys** - moves the instrument tip with the Piper.
3. **INSTRUMENT keys** - drives the adaptor.

**ARM keys** (pane 2):

| Key | Motion |
|---|---|
| `i` / `,` | tip forward / back (away from you / toward you in the SOFA view) |
| `J` / `L` | tip left / right (hold `Shift`) |
| `t` / `b` | tip up / down |
| `j` / `l` | turn the instrument about the vertical axis through the tip |
| `k` | stop |

**INSTRUMENT keys** (pane 3):

| Key | Motion |
|---|---|
| `j` / `l` | roll the instrument about its shaft |
| `i` / `,` | wrist pitch |
| `t` / `b` | wrist yaw (both jaws turn together) |
| `J` / `L` | close / open the jaws (hold `Shift`) |
| `k` | stop |

**SOFA pane** (pane 1): type `a` and `Enter` to re-anchor: the instrument stays where it is in the scene, and the Piper's current pose becomes the new reference, like the clutch pedal on a da Vinci console. Type `r` and `Enter` to reset the scene.

**Mouse in the SOFA window**: scroll to zoom, drag with the left button to rotate the view, drag with the right button to move it, press `c` to go back to the starting view.

> [!TIP]
> A key keeps the motion going until you press `k` or another key, so you don't need to hold it down. `q` / `z` in a keys pane make that keyboard faster / slower.

Try to pick up the ring. Right after the start (or after `r` + `Enter`) the instrument wrist is at about (0, 65, 20) mm and the jaws are open:

1. ARM `J` for about half a second, then `k`, and ARM `,` for about half a second, then `k`. The wrist should be at about (26, 65, -3) mm, with the jaws over the near edge of the ring.
2. ARM `b` until the wrist is at a height of about 27 mm.
3. INSTRUMENT `J` until the status line says `grasped`.
4. ARM `t` to lift the ring.

The program has more options:

| Option | Effect |
|---|---|
| `--rings` | ring scene; without it you get the organ scene |
| `--sliders` | move the arm with one slider per joint instead of the ARM keys |
| `--follow` | real arm: show the arm's own joint positions (see [Real arm](#real-arm)) |
| `--no-tile` | don't open the terminal and don't move windows; attach with `tmux attach -t davinci_piper` |
| `--motion-scale 0.5` | the instrument moves half as far in the scene as the arm moves |

Everything runs in a tmux session called `davinci_piper`. Its second window (`Ctrl+b`, then `n`) shows the ROS programs. To stop everything:
```bash
tmux kill-session -t davinci_piper
```

Here are some links about tmux: [Getting started with Tmux](https://linuxize.com/post/getting-started-with-tmux/), [Tmux Cheat Sheet](https://tmuxcheatsheet.com/)

## Good to know
- **The arm's reach is small.** From the starting pose the tip reaches roughly 240 mm forward, 115 mm back, 80 mm left, 120 mm right, 95 mm up and 200 mm down, and the instrument turns only about 9 degrees each way. When a key would take the arm past a joint limit, the arm stops and the ROS window (`Ctrl+b`, `n`) prints `Arm cannot move further this way`. Press the opposite key to move again.
- **The jaws are not directly below the wrist.** The Piper holds the instrument tilted, with the shaft about 23 degrees from vertical. The jaws end up about 9 mm forward of the wrist position in the status line and 22 mm below it.
- **Both jaws have to touch the ring to grasp it.** If the jaws are a few millimetres too high or to the side, they close completely (grip 0) without grasping. Open them, move, and try again. Keep the roll near 0, so the jaws close across the ring and not along it.
- **A grasped ring hangs down from the jaws** and swings about the grasp point. The scene counts a ring as placed when it lies flat around a peg. Lowering it straight onto a peg leaves it hanging over the top of the peg. What works: set the bottom edge of the ring on the board about 20 mm before the peg, swing the instrument forward over the peg so the ring tips over and lies down around it, then open the jaws.
- **There is no trocar.** In a real operation the shaft passes through a port in the body wall; here the shaft moves freely.
- **The instrument dimensions are estimates.** The adaptor model comes from its CAD files; the instrument housing and shaft in [piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) are estimated. Change them there to match your instrument.

## Real arm
> [!CAUTION]
> Not tested yet. These steps follow the AgileX documentation. Stay out of the arm's reach while it moves, and keep the emergency stop at hand.

Plug the Piper's USB-CAN adapter into your computer. Inside the container, bring up the CAN interface:
```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts
bash can_activate.sh
```
This brings up `can0` at 1 000 000 bit/s. Check that the arm is talking:
```bash
ip -details link show can0     # state UP, bitrate 1000000
candump can0                   # frames scroll by while the arm is powered
```

Start the driver, and first only watch the real arm in RViz (the sliders do not move it):
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper \
  follow:=true control:=false
```

When that works, stop it with `Ctrl+c`. Start the driver alone, without its RViz, because `run_davinci_piper` starts its own RViz and robot model with the adaptor:
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper
```
and in a second terminal (`./run_piper.sh`):
```bash
run_davinci_piper --rings --follow
```
With `--follow`, RViz and SOFA show the arm's measured joint positions, and the ARM keys start from the arm's current pose. The driver moves the arm to what the ARM keys publish on `control/joint_states`.

The adaptor's own motors are not connected to ROS yet; the INSTRUMENT keys only move the instrument in the simulation.

## Working on your project
All the files are in the [docker](docker) folder. The Dockerfile copies them into the image:

| File | In the container | What it does |
|---|---|---|
| [davinci/run_davinci_piper.sh](docker/davinci/run_davinci_piper.sh) | `run_davinci_piper` | starts the tmux session with all the programs |
| [davinci/tile_windows.sh](docker/davinci/tile_windows.sh) | `/root/davinci_piper/` | opens the keys terminal and arranges the windows |
| [davinci/davinci_piper.launch.py](docker/davinci/davinci_piper.launch.py) | `/root/davinci_piper/` | ROS launch file: robot model, RViz, ARM keys controller or joint sliders |
| [davinci/piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) | `/root/davinci_piper/` | robot model: Piper, adaptor, instrument, and the `instrument_wrist` frame that SOFA follows |
| [davinci/piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py) | `/root/davinci_piper/` | ARM keys: moves the instrument tip, solves the inverse kinematics, publishes joint positions |
| [davinci/piper_tool_bridge.py](docker/davinci/piper_tool_bridge.py) | `/root/davinci_piper/` | sends the pose of `instrument_wrist` to SOFA |
| [sofa/twist_socket_bridge.py](docker/sofa/twist_socket_bridge.py) | `/opt/sofa_teleop/` | sends the INSTRUMENT keys to SOFA |
| [sofa/davinci_piper_teleop.py](docker/sofa/davinci_piper_teleop.py) | `/opt/sofa_teleop/` | the SOFA side: places the Piper in the scene and moves the instrument |
| [sofa/sofa_env_sofa25.patch](docker/sofa/sofa_env_sofa25.patch) | applied to `/opt/sofa_env` | ports LapGym to SOFA v25.12 and adds the instrument wrist and independent jaws |
| [sofa/lapgym_keyboard_teleop.py](docker/sofa/lapgym_keyboard_teleop.py), [sofa/run_sofa_teleop.sh](docker/sofa/run_sofa_teleop.sh) | `run_sofa_teleop` | LapGym's own gripper on the organ scene with keyboard control, without the Piper |
| [sofa/smoke_test.py](docker/sofa/smoke_test.py) | `/opt/sofa_teleop/` | loads all 14 LapGym scenes and runs a few steps in each |
| [sofa/sofa-python](docker/sofa/sofa-python) | `sofa-python` | Python with SOFA and LapGym; use it to run SOFA scripts |

SOFA scripts run with `sofa-python` (Python 3.12 in its own environment), not with the system `python3` that ROS uses. Check that all scenes load with:
```bash
sofa-python /opt/sofa_teleop/smoke_test.py
```

The two UDP messages SOFA receives on port 5006 are JSON:
```
{"tool_pose": [x, y, z, qx, qy, qz, qw]}     pose of instrument_wrist in the Piper base frame, metres
{"vel": [vx, vy, vz, wx, wy, wz]}            the INSTRUMENT keys (a geometry_msgs/Twist)
```
To move the instrument tip from your own program, publish a `geometry_msgs/Twist` on `/piper/cmd_vel`, the same message the ARM keys send. `linear` moves the tip in the Piper base frame and `angular.z` turns the instrument; a value of 0.5 for `linear` (1.0 for `angular.z`) gives the full speed of 40 mm/s (0.25 rad/s).

Changes you make inside the container are lost when you remove it (`docker rm -f piper-jazzy`). Change the files in the `docker` folder and rebuild the image instead, or copy a changed file in with `docker cp <file> piper-jazzy:<path>`.


## License
The code in this repository is under the [MIT license](LICENSE). The adaptor's CAD model, which the Docker build downloads, is under GPL-3.0 (see its repository).

[^1]: AgileX Piper: a 6-joint arm controlled over CAN. The ROS 2 driver is [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2), branch `ros2`, with the Python SDK [pyAgxArm](https://github.com/agilexrobotics/pyAgxArm).
[^2]: [Open-Platform adaptor for da Vinci Si instruments](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Its CAD model (GPL-3.0) is downloaded during the Docker build, not stored in this repository.
[^3]: [sofa_env](https://github.com/ScheiklP/sofa_env) by Paul Maria Scheikl et al., the LapGym collection of surgical scenes for SOFA (MIT license). This repository only contains a patch to it; the build downloads the original.
