Click in the upper right corner for Table of Contents ↗️ | [Hrvatska verzija](README.md)

# Piper da Vinci Simulation
Simulation of an [AgileX Piper](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) arm holding a da Vinci Si instrument through an [open-platform adaptor](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). The arm is shown in [RViz](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html) ([ROS 2 Jazzy](https://docs.ros.org/en/jazzy/)), and the instrument works in the [LapGym](https://github.com/ScheiklP/sofa_env) surgical scenes in the [SOFA](https://www.sofa-framework.org/) simulator.

[![Demo](media/demo.gif)](media/demo.mp4)

> [!NOTE]
> If you run into a problem, check the [Issues](../../issues) or open a new one with a description, your operating system and the full error output.

> [!IMPORTANT]
> Tested in simulation only.

## Setting up Docker
Docker packs everything the simulation needs (ROS 2 Jazzy, SOFA, LapGym, the Piper driver) into one container, so none of it has to be installed on your computer. You can think of a container as a lightweight virtual machine. An image is a template you build once; a container is a copy of the image that you start and work in.

You need Linux with a desktop and about 12 GB of disk space.

1. Install the Docker engine following the [official instructions](https://docs.docker.com/engine/install/ubuntu/).
2. Follow the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) to use Docker as a normal user. Without them every `docker` command has to be run with `sudo`.

More on Docker: [official documentation](https://docs.docker.com/get-started/), [LARICS Docker wiki](https://github.com/larics/docker_files/wiki).

## Installing the simulation
```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
docker build -t piper-jazzy .
./run_piper.sh
```

`docker build` builds the `piper-jazzy` image, and `run_piper.sh` creates a container with the same name from it and opens a shell in it. Running `./run_piper.sh` again opens another terminal in the same container. After rebuilding the image, remove the old container with `docker rm -f piper-jazzy`, otherwise you keep working in the container made from the old image.

## Running
Inside the container:
```bash
run_davinci_piper --rings
```
SOFA, RViz and a terminal with three panes open: SOFA messages, ARM keys and INSTRUMENT keys. Click the pane you want to type in. The keys work as in [teleop_twist_keyboard](https://github.com/ros2/teleop_twist_keyboard):

| Key | ARM keys | INSTRUMENT keys |
|---|---|---|
| `i` / `,` | tip forward / back | wrist pitch |
| `J` / `L` | tip left / right | close / open jaws |
| `t` / `b` | tip up / down | wrist yaw |
| `j` / `l` | turn about the vertical axis | roll |
| `k` | stop | stop |

In the SOFA pane, `r` + `Enter` resets the scene and `a` + `Enter` takes the arm's current pose as the new reference. Without `--rings` you get the organ scene.

Everything runs in the [tmux](https://github.com/tmux/tmux/wiki) session `davinci_piper` ([getting started](https://linuxize.com/post/getting-started-with-tmux/), [cheat sheet](https://tmuxcheatsheet.com/)). To stop:
```bash
tmux kill-session -t davinci_piper
```

## Adaptor and instrument
The robot model is [docker/davinci/piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) ([xacro](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Using-Xacro-to-Clean-Up-a-URDF-File.html), [URDF](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html)). It includes the official Piper model from `agx_arm_description` and attaches the adaptor and the instrument to its last link `link6` with fixed joints:

```
link6 ── flange_link ── davinci_adapter ─┬─ instrument_housing
         (flange)       (adaptor STL)    └─ instrument_shaft ── instrument_wrist
```

- **The adaptor** is the CAD model from the [adaptor repository](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Docker downloads it during the build to `/root/davinci_piper/meshes/davinci_si_adapter.stl`. The STL is in millimetres, hence `scale="0.001 0.001 0.001"`. The `adapter_mount` joint lifts it by the flange thickness (10.5 mm) and rotates it 90° about x, so the mounting plate lies on the flange.
- **The instrument** is not in the CAD model, so its housing (a box) and shaft (a cylinder) are estimates. The dimensions are xacro properties at the top of the file (`housing_size`, `shaft_length`, ...).
- **`instrument_wrist`** is the frame at the end of the shaft. Its z axis points along the shaft and its x axis is the jaw hinge axis. This frame is the only link between the arm and SOFA: `piper_tool_bridge.py` sends its pose to SOFA, and the ARM keys move it.

### Your own adaptor
1. Put your adaptor's STL in `docker/davinci/meshes/`, e.g. `docker/davinci/meshes/my_adapter.stl`. The Dockerfile copies the `davinci` folder to `/root/davinci_piper/`.
2. In `piper_davinci.urdf.xacro`, change the mesh in the `davinci_adapter` link to `${mesh_dir}/my_adapter.stl`. If the STL is in metres, use `scale="1 1 1"`.
3. Change the `origin` of the `adapter_mount` joint so the adaptor plate lies on the flange: `xyz` is the offset and `rpy` the rotation (radians) of your CAD frame relative to the flange.
4. Change the instrument properties, especially `shaft_axis_y`, `shaft_start_z` and `shaft_length`, so that `instrument_wrist` is at the tip of your instrument.
5. Check the model and look at it in RViz (enable TF in RViz to see the frames):
   ```bash
   xacro /root/davinci_piper/piper_davinci.urdf.xacro > /tmp/robot.urdf && check_urdf /tmp/robot.urdf
   run_davinci_piper --rings --sliders
   ```

While trying things out you can edit the files directly in the container (`/root/davinci_piper/`) or copy them in with `docker cp`. When the model is done, rebuild the image. The ARM keys read the model from `robot_description`, so they work with the new adaptor without changes. If your instrument is much longer or shorter, change the starting pose `READY_POSE` in [piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py), because the arm's reach depends on it.

## Real arm
> [!CAUTION]
> Not tested. Follow the [AgileX instructions](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) and keep the emergency stop at hand.

```bash
bash ~/agx_arm_ws/src/agx_arm_ros/scripts/can_activate.sh
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper
# in a second terminal (./run_piper.sh):
run_davinci_piper --rings --follow
```
The adaptor's motors are not connected to ROS; the INSTRUMENT keys work in simulation only.

## Working on your project
The code is in the [docker](docker) folder: the ROS part in [docker/davinci](docker/davinci), the SOFA part in [docker/sofa](docker/sofa). To move the instrument tip from your own program, publish a [geometry_msgs/Twist](https://docs.ros2.org/latest/api/geometry_msgs/msg/Twist.html) on `/piper/cmd_vel`. Run SOFA scripts with `sofa-python`. Changes inside the container are lost when it is removed, so edit the files in the `docker` folder and rebuild the image.

## License
[MIT](LICENSE). The adaptor's CAD model (GPL-3.0) and [sofa_env](https://github.com/ScheiklP/sofa_env) (MIT) are downloaded during the image build.
