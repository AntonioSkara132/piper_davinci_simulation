Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
Simulacija ruke [AgileX Piper](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) koja drži da Vinci Si instrument preko [otvorenog adaptera](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Ruka se prikazuje u [RViz-u](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html) ([ROS 2 Jazzy](https://docs.ros.org/en/jazzy/)), a instrument radi u kirurškim scenama [LapGym](https://github.com/ScheiklP/sofa_env) u simulatoru [SOFA](https://www.sofa-framework.org/).

[![Demo](media/demo.gif)](media/demo.mp4)

> [!NOTE]
> Ako naiđete na problem, pogledajte [Issues](../../issues) ili otvorite novi issue s opisom, operacijskim sustavom i cijelim ispisom greške.

> [!IMPORTANT]
> Testirano samo u simulaciji.

## Postavljanje Dockera
Docker u jedan kontejner pakira sve što je potrebno za simulaciju (ROS 2 Jazzy, SOFA, LapGym, upravljački program za Piper), pa ništa od toga ne morate instalirati na svoje računalo. Kontejner možete zamisliti kao lagani virtualni stroj. Slika (image) je predložak koji se izgradi jednom, a kontejner je primjerak slike koji pokrećete i u kojem radite.

Potrebni su Linux s grafičkim sučeljem i oko 12 GB prostora na disku.

1. Instalirajte Docker engine prema [službenim uputama](https://docs.docker.com/engine/install/ubuntu/).
2. Slijedite [korake nakon instalacije](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) kako biste Docker mogli koristiti kao običan korisnik. Bez toga svaku `docker` naredbu morate pokretati sa `sudo`.

Više o Dockeru: [službena dokumentacija](https://docs.docker.com/get-started/), [LARICS Docker wiki](https://github.com/larics/docker_files/wiki).

## Instalacija simulacije
```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
docker build -t piper-jazzy .
./run_piper.sh
```

`docker build` izgradi sliku `piper-jazzy`, a `run_piper.sh` iz nje stvori kontejner istog imena i otvori ljusku u njemu. Ponovnim pokretanjem `./run_piper.sh` otvarate novi terminal u istom kontejneru. Nakon ponovne izgradnje slike obrišite stari kontejner s `docker rm -f piper-jazzy`, inače i dalje radite u kontejneru iz stare slike.

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

## Adapter i instrument
Model robota je [docker/davinci/piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) ([xacro](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Using-Xacro-to-Clean-Up-a-URDF-File.html), [URDF](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html)). Uključuje službeni model Pipera iz `agx_arm_description` i na njegov zadnji link `link6` dodaje adapter i instrument fiksnim zglobovima:

```
link6 ── flange_link ── davinci_adapter ─┬─ instrument_housing
         (prirubnica)   (STL adaptera)   └─ instrument_shaft ── instrument_wrist
```

- **Adapter** je CAD model iz [repozitorija adaptera](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Docker ga preuzima tijekom izgradnje u `/root/davinci_piper/meshes/davinci_si_adapter.stl`. STL je u milimetrima, pa ima `scale="0.001 0.001 0.001"`. Zglob `adapter_mount` podiže ga za debljinu prirubnice (10.5 mm) i zakreće za 90° oko osi x, tako da ploča za montažu leži na prirubnici.
- **Instrument** nije u CAD modelu, pa su kućište (kvadar) i osovina (valjak) procijenjeni. Dimenzije su xacro svojstva na vrhu datoteke (`housing_size`, `shaft_length`, ...).
- **`instrument_wrist`** je okvir na kraju osovine. Os z gleda duž osovine, a os x je os zgloba čeljusti. Samo taj okvir povezuje ruku sa SOFA-om: `piper_tool_bridge.py` šalje njegovu pozu SOFA-i, a upravljanje tipkama pomiče upravo njega.

### Vlastiti adapter
1. Stavite STL svog adaptera u `docker/davinci/meshes/`, npr. `docker/davinci/meshes/moj_adapter.stl`. Dockerfile kopira mapu `davinci` u `/root/davinci_piper/`.
2. U `piper_davinci.urdf.xacro` promijenite putanju u linku `davinci_adapter` na `${mesh_dir}/moj_adapter.stl`. Ako je STL u metrima, stavite `scale="1 1 1"`.
3. Promijenite `origin` zgloba `adapter_mount` tako da ploča adaptera leži na prirubnici: `xyz` je pomak, a `rpy` zakret (u radijanima) okvira vašeg CAD modela u odnosu na prirubnicu.
4. Promijenite svojstva instrumenta, a posebno `shaft_axis_y`, `shaft_start_z` i `shaft_length`, tako da `instrument_wrist` bude na vrhu vašeg instrumenta.
5. Provjerite model i pogledajte ga u RViz-u (u RViz-u uključite TF da vidite okvire):
   ```bash
   xacro /root/davinci_piper/piper_davinci.urdf.xacro > /tmp/robot.urdf && check_urdf /tmp/robot.urdf
   run_davinci_piper --rings --sliders
   ```

Dok isprobavate, datoteke možete mijenjati izravno u kontejneru (`/root/davinci_piper/`) ili ih kopirati s `docker cp`. Kad je model gotov, ponovno izgradite sliku. Upravljanje tipkama čita model iz `robot_description`, pa radi s novim adapterom bez promjena. Ako je vaš instrument znatno duži ili kraći, promijenite početnu pozu `READY_POSE` u [piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py), jer o njoj ovisi koliko ruka može doseći.

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
