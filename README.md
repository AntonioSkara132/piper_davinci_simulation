Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
## Uvod
U ovom projektu pomoću simulatora SOFA simuliramo kiruršku scenu iz LapGyma u kojoj ruka [AgileX Piper](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) preko adaptera drži instrument da Vinci Si. Simulacija je napravljena kao privremena zamjena za stvarnog robota: na njoj možete razvijati i isprobavati upravljanje dok robot nije dostupan. Ruka se upravlja istim ROS 2 topicima koje koristi upravljački program stvarne ruke.

- **[SOFA](https://www.sofa-framework.org/)** je simulator otvorenog koda za medicinske simulacije. Računa deformacije mekih tkiva, sudare i dodir, pa se vidi kako instrument hvata i pomiče predmete.
- **[LapGym](https://github.com/ScheiklP/sofa_env)** (sofa_env) je skup scena za SOFA-u koje oponašaju laparoskopske zadatke. Ovdje koristimo dvije: premještanje prstenova i hvatanje tkiva na organu.
- **[ROS 2 Jazzy](https://docs.ros.org/en/jazzy/)** povezuje programe porukama na topicima, a **[RViz](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html)** prikazuje model ruke s adapterom i instrumentom.
- **[Docker](https://docs.docker.com/get-started/)** pakira sve to u jedan kontejner, pa na svoje računalo instalirate samo Docker (vidi [Postavljanje Dockera](#postavljanje-dockera)).

Kao primjer upravljanja napravljeno je sučelje s tipkovnicom: [teleop_twist_keyboard](https://github.com/ros2/teleop_twist_keyboard) šalje poruke `Twist`, a [piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py) iz njih inverznom kinematikom računa položaje zglobova. **To je samo primjer:** upravljanje rukom pišete sami, a ovaj čvor možete koristiti kao polazište. Svoj čvor pokrenite uz `run_davinci_piper --rings --no-arm`, a topici koje treba koristiti opisani su u [Topici i TF](#topici-i-tf).

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

Sve radi u [tmux](https://github.com/tmux/tmux/wiki) sesiji `davinci_piper` ([kratki uvod](https://github.com/tmux/tmux/wiki/Getting-Started), [popis naredbi](https://tmuxcheatsheet.com/)). Zaustavljanje:
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
   ```xml
   <link name="davinci_adapter">
     <visual>
       <geometry>
         <mesh filename="${mesh_dir}/moj_adapter.stl" scale="0.001 0.001 0.001"/>
       </geometry>
       <material name="adapter_grey"><color rgba="0.75 0.77 0.82 1"/></material>
     </visual>
     <inertial>
       ...
     </inertial>
   </link>
   ```
3. Promijenite `origin` zgloba `adapter_mount` tako da ploča adaptera leži na prirubnici: `xyz` je pomak, a `rpy` zakret (u radijanima) okvira vašeg CAD modela u odnosu na prirubnicu.
4. Promijenite svojstva instrumenta, a posebno `shaft_axis_y`, `shaft_start_z` i `shaft_length`, tako da `instrument_wrist` bude na vrhu vašeg instrumenta.
5. Provjerite model i pogledajte ga u RViz-u (u RViz-u uključite TF da vidite okvire):
   ```bash
   xacro /root/davinci_piper/piper_davinci.urdf.xacro > /tmp/robot.urdf && check_urdf /tmp/robot.urdf
   run_davinci_piper --rings --sliders
   ```

Dok isprobavate, datoteke možete mijenjati izravno u kontejneru (`/root/davinci_piper/`) ili ih kopirati s `docker cp`. Kad je model gotov, ponovno izgradite sliku. Upravljanje tipkama čita model iz `robot_description`, pa radi s novim adapterom bez promjena. Ako je vaš instrument znatno duži ili kraći, promijenite početnu pozu `READY_POSE` u [piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py), jer o njoj ovisi koliko ruka može doseći.

## Topici i TF
```
ARM keys ──/piper/cmd_vel──> piper_cartesian_jog ──/control/joint_states──> robot_state_publisher ──TF──> piper_tool_bridge ──UDP──> SOFA
                             (inverzna kinematika)                                                (base_link → instrument_wrist)

INSTRUMENT keys ──/davinci/cmd_vel──> twist_socket_bridge ──UDP──> SOFA (roll, pitch, yaw, hvat)
```

| Topic / okvir | Tip | Što je |
|---|---|---|
| `/piper/cmd_vel` | `geometry_msgs/Twist` | brzina vrha instrumenta u okviru `base_link`: `linear` 0.5 = 40 mm/s, `angular.z` 1.0 = 0.25 rad/s okretanja oko okomite osi |
| `/control/joint_states` | `sensor_msgs/JointState` | zadani položaji zglobova `joint1` … `joint6` u radijanima; stvarnu ruku upravljački program pomiče u njih |
| `/feedback/joint_states` | `sensor_msgs/JointState` | izmjereni položaji zglobova stvarne ruke, objavljuje ih upravljački program |
| `/davinci/cmd_vel` | `geometry_msgs/Twist` | tipke instrumenta (roll, pitch, yaw, hvat); idu samo u SOFA-u |
| TF `base_link` → `instrument_wrist` | TF | poza zgloba instrumenta koju SOFA prati |

RViz i SOFA prikazuju `/control/joint_states`, a s opcijom `--follow` `/feedback/joint_states`. Iz vlastitog programa rukom upravljate na jedan od dva načina:

- objavljujete `Twist` na `/piper/cmd_vel`, isto kao tipke ruke, ili
- pokrenete `run_davinci_piper --rings --no-arm`, tako da tipke ruke ne rade, i sami objavljujete `JointState` na `/control/joint_states`, s trenutnim vremenom u `header.stamp`.

## Rad na projektu
Kod je u mapi [docker](docker). Upravljački program (driver) za Piper nije u njoj: Dockerfile ga pri izgradnji slike klonira iz [AgileX repozitorija](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2) u `/root/agx_arm_ws`. U driver nismo ništa dodavali niti smo ga mijenjali.

```
docker/
├── Dockerfile
├── run_piper.sh                  pokreće kontejner piper-jazzy na računalu
│
├── davinci/          → u kontejneru /root/davinci_piper/   (ROS 2 dio)
│   ├── piper_davinci.urdf.xacro  model: Piper + adapter + instrument
│   ├── meshes/                   ovdje stavljate STL svog adaptera
│   ├── piper_cartesian_jog.py    /piper/cmd_vel → IK → /control/joint_states
│   ├── piper_tool_bridge.py      TF base_link→instrument_wrist → UDP prema SOFA-i
│   ├── davinci_piper.launch.py   robot_state_publisher, jog/slideri, bridge, RViz
│   ├── davinci_piper.rviz        postavke RViz-a
│   ├── run_davinci_piper.sh      naredba run_davinci_piper (tmux sesija)
│   └── tile_windows.sh           slaže prozore SOFA-e, RViz-a i terminala
│
└── sofa/             → u kontejneru /opt/sofa_teleop/      (SOFA dio)
    ├── davinci_piper_teleop.py   LapGym scena koja prati pozu iz piper_tool_bridge
    ├── lapgym_keyboard_teleop.py upravljanje LapGym hvataljkom tipkama, prozor SOFA-e
    ├── twist_socket_bridge.py    /davinci/cmd_vel → UDP (roll, pitch, yaw, hvat)
    ├── run_sofa_teleop.sh        naredba run_sofa_teleop (LapGym bez Pipera)
    ├── sofa-python               pokreće Python sa SOFA-om
    ├── sofa_env_sofa25.patch     prilagodba sofa_env za SOFA v25.12
    └── smoke_test.py             provjera da se svih 14 LapGym scena pokreće
```

Topici kojima upravljate rukom opisani su u [Topici i TF](#topici-i-tf). SOFA skripte pokreću se sa `sofa-python`. Promjene unutar kontejnera brišu se s kontejnerom, pa mijenjajte datoteke u mapi `docker` i ponovno izgradite sliku.

## Licenca
[MIT](LICENSE). [sofa_env](https://github.com/ScheiklP/sofa_env) (MIT) preuzima se tijekom izgradnje slike.
