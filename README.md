Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
Simulacija ruke [AgileX Piper](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) koja drži da Vinci Si instrument preko [otvorenog adaptera](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Ruka se prikazuje u [RViz-u](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html) ([ROS 2 Jazzy](https://docs.ros.org/en/jazzy/)), a instrument radi u kirurškim scenama [LapGym](https://github.com/ScheiklP/sofa_env) u simulatoru [SOFA](https://www.sofa-framework.org/).

[![Demo](media/demo.gif)](media/demo.mp4)

> [!NOTE]
> Ako naiđete na problem, pogledajte [Issues](../../issues) ili otvorite novi issue s opisom, operacijskim sustavom i cijelim ispisom greške.

> [!IMPORTANT]
> Testirano samo u simulaciji.

## Instalacija
Potrebni su Linux s grafičkim sučeljem, oko 12 GB prostora na disku i [Docker](https://docs.docker.com/engine/install/ubuntu/). Preporučeno je i [korištenje Dockera bez sudo](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).

```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
docker build -t piper-jazzy .
./run_piper.sh
```

`run_piper.sh` stvara kontejner `piper-jazzy` i otvara ljusku u njemu. Ponovnim pokretanjem otvarate novi terminal u istom kontejneru, a `docker rm -f piper-jazzy` briše kontejner (npr. nakon ponovne izgradnje slike). Više o Dockeru: [službena dokumentacija](https://docs.docker.com/get-started/), [LARICS Docker wiki](https://github.com/larics/docker_files/wiki).

## Pokretanje
Unutar kontejnera:
```bash
run_davinci_piper --rings
```
Otvaraju se SOFA, RViz i terminal s tri okna: poruke iz SOFA-e, tipke ruke (ARM keys) i tipke instrumenta (INSTRUMENT keys). Kliknite na okno u kojem želite tipkati. Tipke rade kao u [teleop_twist_keyboard](https://github.com/ros2/teleop_twist_keyboard):

| Tipka | ARM keys | INSTRUMENT keys |
|---|---|---|
| `i` / `,` | vrh naprijed / natrag | pitch zgloba |
| `J` / `L` | vrh lijevo / desno | zatvaranje / otvaranje čeljusti |
| `t` / `b` | vrh gore / dolje | yaw zgloba |
| `j` / `l` | okretanje oko okomite osi | roll |
| `k` | stop | stop |

U oknu SOFA-e `r` + `Enter` ponovno pokreće scenu, a `a` + `Enter` uzima trenutnu pozu ruke kao novu referencu. Bez `--rings` pokreće se scena s organom.

Sve radi u [tmux](https://github.com/tmux/tmux/wiki) sesiji `davinci_piper` ([kratki uvod](https://linuxize.com/post/getting-started-with-tmux/), [popis naredbi](https://tmuxcheatsheet.com/)). Zaustavljanje:
```bash
tmux kill-session -t davinci_piper
```

## Stvarna ruka
> [!CAUTION]
> Nije testirano. Slijedite [AgileX upute](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) i držite tipku za zaustavljanje u nuždi pri ruci.

```bash
bash ~/agx_arm_ws/src/agx_arm_ros/scripts/can_activate.sh
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py can_port:=can0 arm_type:=piper effector_type:=agx_gripper
# u drugom terminalu (./run_piper.sh):
run_davinci_piper --rings --follow
```
Motori adaptera nisu spojeni na ROS; tipke instrumenta rade samo u simulaciji.

## Rad na projektu
Kod je u mapi [docker](docker): ROS dio u [docker/davinci](docker/davinci), SOFA dio u [docker/sofa](docker/sofa). Vrh instrumenta možete pomicati iz vlastitog programa objavljivanjem [geometry_msgs/Twist](https://docs.ros2.org/latest/api/geometry_msgs/msg/Twist.html) na `/piper/cmd_vel`. SOFA skripte pokreću se sa `sofa-python`. Promjene unutar kontejnera brišu se s kontejnerom, pa mijenjajte datoteke u mapi `docker` i ponovno izgradite sliku.

## Licenca
[MIT](LICENSE). CAD model adaptera (GPL-3.0) i [sofa_env](https://github.com/ScheiklP/sofa_env) (MIT) preuzimaju se tijekom izgradnje slike.
