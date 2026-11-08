Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
Simulacija ruke [AgileX Piper](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) koja drži da Vinci Si instrument preko adaptera. Ruka se prikazuje u [RViz-u](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html) ([ROS 2 Jazzy](https://docs.ros.org/en/jazzy/)), a instrument radi u kirurškim scenama [LapGym](https://github.com/ScheiklP/sofa_env) u simulatoru [SOFA](https://www.sofa-framework.org/).

[![Demo](media/demo.gif)](media/demo.mp4)

> [!NOTE]
> Ako naiđete na problem, pogledajte [Issues](../../issues) ili otvorite novi issue s opisom, operacijskim sustavom i cijelim ispisom greške.

> [!IMPORTANT]
> Testirano samo u simulaciji.

## Postavljanje Dockera
Docker u jedan kontejner pakira sve što je potrebno za simulaciju (ROS 2 Jazzy, SOFA, LapGym, upravljački program za Piper), pa ništa od toga ne morate instalirati na svoje računalo. Kontejner možete zamisliti kao lagani virtualni stroj. Slika (image) je predložak koji se izgradi jednom, a kontejner je primjerak slike koji pokrećete i u kojem radite.

Potrebni su Linux s grafičkim sučeljem (ili Windows, vidi [Windows (WSL2)](#windows-wsl2)) i oko 12 GB prostora na disku.

1. Instalirajte Docker engine prema [službenim uputama](https://docs.docker.com/engine/install/ubuntu/).
2. Slijedite [korake nakon instalacije](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) kako biste Docker mogli koristiti kao običan korisnik. Bez toga svaku `docker` naredbu morate pokretati sa `sudo`.

Više o Dockeru: [službena dokumentacija](https://docs.docker.com/get-started/), [LARICS Docker wiki](https://github.com/larics/docker_files/wiki).

### Windows (WSL2)
> [!WARNING]
> Nije testirano. Za stvarnu ruku treba Linux, jer WSL2 nema upravljačke programe za CAN.

Na Windowsima se sve radi u Ubuntuu unutar [WSL2](https://learn.microsoft.com/en-us/windows/wsl/about) (Windows Subsystem for Linux). Potreban je Windows 11 ili Windows 10 verzija 21H2 ili novija, jer tek one mogu prikazivati prozore Linux programa ([WSLg](https://github.com/microsoft/wslg)).

1. Otvorite PowerShell kao administrator, instalirajte WSL2 s Ubuntuom 24.04 i ponovno pokrenite računalo ([upute](https://learn.microsoft.com/en-us/windows/wsl/install)):
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
2. Nakon ponovnog pokretanja otvorite **Ubuntu 24.04** iz izbornika Start i upišite korisničko ime i lozinku za Linux. Sve sljedeće naredbe upisujete u taj Ubuntu terminal.
3. U PowerShellu provjerite da Ubuntu radi pod WSL verzijom 2 (stupac `VERSION`) i ažurirajte WSL:
   ```powershell
   wsl -l -v
   wsl --update
   ```
4. U Ubuntu terminalu instalirajte Docker Engine i napravite korake nakon instalacije, isto kao na Linuxu (koraci 1 i 2 gore). Zatim instalirajte `xhost`, koji koristi `run_piper.sh`:
   ```bash
   sudo apt install -y x11-xserver-utils
   ```
5. Nastavite s [Instalacijom simulacije](#instalacija-simulacije) u Ubuntu terminalu. Repozitorij klonirajte u Ubuntu (npr. `cd ~`), a ne u Windows mapu pod `/mnt/c`, jer bi Git ondje mogao promijeniti završetke redaka u skriptama i one se onda ne bi pokretale.

WSL2 obično nema `/dev/dri`, pa RViz i SOFA crtaju softverski; to je sporije, ali dovoljno. Ako se prozori ne razmjeste sami, razmjestite ih mišem.

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
         (prirubnica)   (vaš adapter)    └─ instrument_shaft ── instrument_wrist
```

- **Adapter** nije uključen: model adaptera dodajete sami (vidi dolje). Dok ga ne dodate, RViz prikazuje instrument bez adaptera. Okvir `davinci_adapter` i pomaci instrumenta postavljeni su za [otvoreni adapter za da Vinci Si instrumente](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments): zglob `adapter_mount` podiže okvir adaptera za debljinu prirubnice (10.5 mm) i zakreće ga za 90° oko osi x.
- **Instrument** su procijenjeni kvadar (kućište) i valjak (osovina). Dimenzije su xacro svojstva na vrhu datoteke (`housing_size`, `shaft_length`, ...).
- **`instrument_wrist`** je okvir na kraju osovine. Os z gleda duž osovine, a os x je os zgloba čeljusti. Samo taj okvir povezuje ruku sa SOFA-om: `piper_tool_bridge.py` šalje njegovu pozu SOFA-i, a upravljanje tipkama pomiče upravo njega.

### Dodavanje adaptera
1. Stavite STL svog adaptera u [docker/davinci/meshes/](docker/davinci/meshes), npr. `docker/davinci/meshes/moj_adapter.stl`. Dockerfile kopira tu mapu u `/root/davinci_piper/meshes/`.
2. U `piper_davinci.urdf.xacro`, u linku `davinci_adapter`, maknite oznake komentara oko bloka `<visual>` i upišite ime svoje datoteke. Ako je STL u metrima, a ne u milimetrima, stavite `scale="1 1 1"`.
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
[MIT](LICENSE). [sofa_env](https://github.com/ScheiklP/sofa_env) (MIT) preuzima se tijekom izgradnje slike.
