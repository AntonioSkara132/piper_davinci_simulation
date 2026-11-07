Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
Dobro došli! Ove upute pomoći će vam da postavite sve što je potrebno za upravljanje kirurškim instrumentom da Vinci koji drži robotska ruka AgileX Piper, najprije u simulaciji, a kasnije i na stvarnoj ruci.

> [!NOTE]
> Ako tijekom instalacije naiđete na grešku ili problem, najprije pogledajte karticu [Issues](../../issues); možda je problem već riješen. Ako nije, otvorite novi issue.

## Uvod
Robot je **AgileX Piper**, mala ruka sa 6 zglobova[^1]. Na njezinoj prirubnici nalazi se **otvoreni adapter za da Vinci Si instrumente**[^2], koji drži 8 mm da Vinci Si instrument (EndoWrist). Motori adaptera okreću četiri ulazna diska instrumenta, a oni pokreću:

- **rotaciju** instrumenta oko njegove osovine (roll),
- **pitch zgloba** instrumenta,
- **svaku čeljust zasebno**. Kad se obje čeljusti okreću u istu stranu, to je yaw zgloba; kad se okreću jedna od druge, hvataljka se otvara i zatvara.

Ruka određuje gdje je instrument i kamo je usmjerena njegova osovina. Adapter određuje što radi vrh instrumenta.

Simulacija ima dva dijela:

- **ROS 2 Jazzy** sa službenim AgileX upravljačkim programom [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2). RViz prikazuje Piper s adapterom i instrumentom.
- **SOFA v25.12** s dvije kirurške scene za vježbu iz [LapGym](https://github.com/ScheiklP/sofa_env)[^3]:
  - **prstenovi** (pick_and_place): podignite prsten i stavite ga na stup iste boje,
  - **organ** (grasp_lift_touch): uhvatite žučni mjehur i podignite ga.

  Instrument u ovim scenama ima iste stupnjeve slobode kao adapter: roll, pitch zgloba i dvije neovisne čeljusti.

Sve upravljate s dvije tipkovnice u jednom terminalu: **tipke RUKE** (ARM keys) pomiču vrh instrumenta preko Pipera, a **tipke INSTRUMENTA** (INSTRUMENT keys) upravljaju adapterom. Ovako su dijelovi povezani:

```
ARM keys ──/piper/cmd_vel──> piper_cartesian_jog ──control/joint_states──> robot_state_publisher ──TF──> piper_tool_bridge ──UDP──> SOFA
                             (inverzna kinematika)                         (RViz prikazuje ruku)         (poza instrumenta)

INSTRUMENT keys ──/davinci/cmd_vel──> twist_socket_bridge ──UDP──> SOFA (roll, pitch zgloba, yaw zgloba, hvat)
```

SOFA radi u vlastitom Python okruženju, pa s ROS-om razgovara UDP porukama na istom računalu (port 5006) umjesto ROS topicima. Na stvarnoj ruci AgileX upravljački program čita isti topic `control/joint_states` i pomiče ruku u te položaje zglobova.

> [!IMPORTANT]
> Sve u ovom repozitoriju testirano je samo u simulaciji. Upravljanje stvarnim Piperom ovim programima još nije testirano. Pročitajte odjeljak [Stvarna ruka](#stvarna-ruka) prije nego što pokušate.

## Prijava problema
Ako naiđete na grešku koju ne možete sami riješiti ili zapnete na nekom koraku, otvorite [Issue](../../issues) u ovom repozitoriju. Navedite operacijski sustav i način instalacije, opišite problem i priložite cijeli ispis naredbe koja je dovela do greške. Tako ćete najbrže dobiti pomoć, a pomoći ćete i drugim studentima koji kasnije naiđu na istu grešku.

## Instalacija
Sve se pokreće u **Docker kontejneru**: ROS 2 Jazzy treba Ubuntu 24.04, a SOFA i LapGym trebaju točno određen skup Python paketa. Docker slika sadrži sve to, pa svatko dobije isto okruženje jednom naredbom za izgradnju.

### Instalacija Dockera
Ukratko, Docker je alat koji u jedan kontejner pakira sve što je potrebno za određenu aplikaciju. Možete ga zamisliti kao lagani virtualni stroj koji radi na vašem računalu. Ako želite saznati više, pogledajte [službenu stranicu](https://www.docker.com/). Detaljne upute korak po korak nalaze se u nastavku.

#### Preduvjeti
- Linux s grafičkim sučeljem (X11 ili Wayland). Testirano na Ubuntu 22.04 s GNOME-om na Waylandu.
- Oko 12 GB slobodnog prostora na disku. Slika ima oko 9 GB.
- Grafika: testirano s integriranom AMD grafikom, koju kontejner koristi preko `/dev/dri`. Intel grafika radi na isti način. NVIDIA grafika nije testirana; za nju treba [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) i dodatne opcije za `docker run`.

#### Upute korak po korak
Slijedite ove [upute](https://docs.docker.com/engine/install/ubuntu/) za instalaciju Docker enginea.

Zatim slijedite ove [neobavezne korake](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) kako biste Docker mogli koristiti bez root ovlasti. Ako to preskočite, svaku `docker` naredbu morat ćete pokretati sa `sudo`.

Klonirajte ovaj repozitorij u svoj home ili bilo koji drugi direktorij i uđite u mapu `docker`:
```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
```

Izgradite Docker sliku. Vidjet ćete puno ispisa. Prva izgradnja preuzima nekoliko GB (ROS 2, SOFA, Python paketi), pa traje neko vrijeme. Pričekajte da završi.
```bash
docker build -t piper-jazzy .
```

Kad imate sliku, treba vam kontejner. Skripta `run_piper.sh` ga stvori prvi put i otvori ljusku u njemu:
```bash
./run_piper.sh
```

Kad skripta završi, odzivnik u terminalu promijeni se iz
```bash
<vaše korisničko ime>@<ime vašeg računala>
```
u
```bash
root@<ime vašeg računala>
```
To znači da ste sada "unutar" kontejnera. ROS 2 i upravljački program za Piper već su učitani u svakoj ljusci.

> [!TIP]
> Kratki podsjetnik na naredbe za rad s kontejnerom:
> - Izlaz iz ljuske kontejnera - pritisnite `Ctrl+d`. Kontejner nastavlja raditi u pozadini.
> - Otvaranje još jednog terminala u istom kontejneru - ponovno pokrenite `./run_piper.sh` u novom prozoru terminala.
> - Pokretanje jedne naredbe u kontejneru iz vlastitog terminala - `./run_piper.sh <naredba>`
> - Zaustavljanje kontejnera - `docker stop piper-jazzy`
> - Početak ispočetka iz čiste slike (briše sve što ste promijenili unutar kontejnera) - `docker rm -f piper-jazzy`
> - Nakon ponovne izgradnje slike - `docker rm -f piper-jazzy`, zatim `./run_piper.sh`, kako bi se kontejner napravio iz nove slike.

Što radi `run_piper.sh`:

| Opcija | Zašto |
|---|---|
| `xhost +local:` | dopušta kontejneru da otvara prozore na vašoj radnoj površini |
| `--net=host` | ROS 2 topici vidljivi su na vašem računalu, a kontejner može koristiti CAN sučelje stvarne ruke |
| `--privileged` | potrebno da bi se CAN sučelje podiglo iznutra kontejnera |
| `DISPLAY`, `/tmp/.X11-unix` | prozori RViza i SOFA-e otvaraju se na vašoj radnoj površini |
| `--device /dev/dri` | hardverski OpenGL za RViz i SOFA-u |

> [!WARNING]
> `xhost +local:` dopušta programima svih lokalnih korisnika da crtaju po vašem zaslonu dok se ne odjavite. Na zajedničkom računalu poništite to naredbom `xhost -local:` kad završite.
>
> Zbog `--net=host` svi na istoj mreži s istim `ROS_DOMAIN_ID` vide međusobno ROS topice. U laboratoriju s više studenata dajte svakom računalu vlastiti broj, na primjer `export ROS_DOMAIN_ID=17` (bilo koji broj od 0 do 101).

Opcije izgradnje, dodaju se naredbi `docker build`:

| Opcija | Učinak |
|---|---|
| `--build-arg WITH_SOFA=false` | izostavlja SOFA-u i simulaciju (oko 3 GB manje) |
| `--build-arg WITH_MOVEIT=true` | instalira i MoveIt i gradi `agx_arm_moveit` (nekoliko GB više) |
| `--build-arg AGX_ARM_ROS_REF=ros2 --build-arg PYAGXARM_REF=main` | najnoviji upravljački program i SDK za Piper umjesto testiranih verzija |

### Bez Dockera
Testirana je i podržana samo instalacija s Dockerom. Ako imate Ubuntu 24.04 s ROS 2 Jazzy i želite instalirati izravno na sustav, [Dockerfile](docker/Dockerfile) navodi sve korake redom. Skripte očekuju iste putanje kao u slici: `/opt/sofa`, `/opt/sofa_venv`, `/opt/sofa_env`, `/opt/sofa_teleop` i `/root/davinci_piper`.

## Provjera instalacije na primjeru
Pokrenite scenu s prstenovima. Unutar kontejnera:
```bash
run_davinci_piper --rings
```
ili iz vlastitog terminala, u mapi `docker`:
```bash
./run_piper.sh run_davinci_piper --rings
```

Nakon nekoliko sekundi otvore se tri prozora i ispune zaslon:

```
+--------------+------------------+
|              |      RViz        |
|     SOFA     | (Piper + alat)   |
|   prstenovi  +------------------+
|              | terminal s tipk. |
+--------------+------------------+
```

**Terminal s tipkama** ima tri okna. Kliknite na okno da biste u njemu tipkali:

1. **SOFA** - poruke iz simulacije. Svakih 5 sekundi ispiše statusnu liniju s položajem zgloba instrumenta (u milimetrima), kutovima rolla, pitcha, yawa i hvata te podatkom je li nešto uhvaćeno.
2. **ARM keys** - pomiče vrh instrumenta pomoću Pipera.
3. **INSTRUMENT keys** - upravlja adapterom.

**Tipke RUKE** (okno 2):

| Tipka | Pomak |
|---|---|
| `i` / `,` | vrh naprijed / natrag (od vas / prema vama u prikazu SOFA-e) |
| `J` / `L` | vrh lijevo / desno (držite `Shift`) |
| `t` / `b` | vrh gore / dolje |
| `j` / `l` | okretanje instrumenta oko okomite osi kroz vrh |
| `k` | stop |

**Tipke INSTRUMENTA** (okno 3):

| Tipka | Pomak |
|---|---|
| `j` / `l` | roll instrumenta oko osovine |
| `i` / `,` | pitch zgloba |
| `t` / `b` | yaw zgloba (obje čeljusti se okreću zajedno) |
| `J` / `L` | zatvaranje / otvaranje čeljusti (držite `Shift`) |
| `k` | stop |

**Okno SOFA** (okno 1): upišite `a` i `Enter` za ponovno sidrenje: instrument ostaje gdje jest u sceni, a trenutna poza Pipera postaje nova referenca, kao papučica spojke (clutch) na da Vinci konzoli. Upišite `r` i `Enter` za ponovno pokretanje scene.

**Miš u prozoru SOFA-e**: kotačić za zumiranje, povlačenje lijevom tipkom za okretanje pogleda, povlačenje desnom tipkom za pomicanje pogleda, tipka `c` za povratak na početni pogled.

> [!TIP]
> Tipka nastavlja pomak dok ne pritisnete `k` ili drugu tipku, pa je ne morate držati. `q` / `z` u oknu s tipkama ubrzavaju / usporavaju tu tipkovnicu.

Pokušajte podići prsten. Odmah nakon pokretanja (ili nakon `r` + `Enter`) zglob instrumenta je na otprilike (0, 65, 20) mm, a čeljusti su otvorene:

1. RUKA `J` otprilike pola sekunde, zatim `k`, pa RUKA `,` otprilike pola sekunde, zatim `k`. Zglob bi trebao biti na otprilike (26, 65, -3) mm, a čeljusti iznad bližeg ruba prstena.
2. RUKA `b` dok zglob ne bude na visini od otprilike 27 mm.
3. INSTRUMENT `J` dok statusna linija ne pokaže `grasped`.
4. RUKA `t` za podizanje prstena.

Program ima još opcija:

| Opcija | Učinak |
|---|---|
| `--rings` | scena s prstenovima; bez nje dobijete scenu s organom |
| `--sliders` | pomicanje ruke klizačem za svaki zglob umjesto tipkama RUKE |
| `--follow` | stvarna ruka: prikaz izmjerenih položaja zglobova ruke (vidi [Stvarna ruka](#stvarna-ruka)) |
| `--no-tile` | ne otvara terminal i ne razmješta prozore; spojite se s `tmux attach -t davinci_piper` |
| `--motion-scale 0.5` | instrument se u sceni pomiče upola manje nego ruka |

Sve radi u tmux sesiji `davinci_piper`. Njezin drugi prozor (`Ctrl+b`, zatim `n`) prikazuje ROS programe. Za zaustavljanje svega:
```bash
tmux kill-session -t davinci_piper
```

Nekoliko poveznica o tmuxu: [Getting started with Tmux](https://linuxize.com/post/getting-started-with-tmux/), [Tmux Cheat Sheet](https://tmuxcheatsheet.com/)

## Dobro je znati
- **Doseg ruke je malen.** Iz početne poze vrh doseže otprilike 240 mm naprijed, 115 mm natrag, 80 mm lijevo, 120 mm desno, 95 mm gore i 200 mm dolje, a instrument se okreće samo oko 9 stupnjeva na svaku stranu. Kad bi tipka odvela ruku preko granice zgloba, ruka stane, a ROS prozor (`Ctrl+b`, `n`) ispiše `Arm cannot move further this way`. Pritisnite suprotnu tipku da se ruka opet pomakne.
- **Čeljusti nisu točno ispod zgloba.** Piper drži instrument nagnut, s osovinom oko 23 stupnja od okomice. Čeljusti su oko 9 mm ispred položaja zgloba iz statusne linije i 22 mm ispod njega.
- **Za hvatanje prstena obje čeljusti moraju ga dodirivati.** Ako su čeljusti nekoliko milimetara previsoko ili sa strane, potpuno se zatvore (hvat 0) bez hvatanja. Otvorite ih, pomaknite se i pokušajte ponovno. Držite roll blizu 0, tako da se čeljusti zatvaraju poprijeko prstena, a ne uzduž njega.
- **Uhvaćeni prsten visi s čeljusti** i njiše se oko točke hvata. Scena prsten smatra postavljenim kad leži ravno oko stupa. Ako ga spustite ravno na stup, ostane visjeti preko vrha stupa. Ovo radi: spustite donji rub prstena na podlogu oko 20 mm prije stupa, zamahnite instrumentom naprijed preko stupa tako da se prsten prevrne i legne oko njega, zatim otvorite čeljusti.
- **Nema troakara.** U stvarnoj operaciji osovina prolazi kroz otvor u trbušnoj stijenci; ovdje se osovina slobodno pomiče.
- **Dimenzije instrumenta su procijenjene.** Model adaptera dolazi iz njegovih CAD datoteka; kućište i osovina instrumenta u [piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) su procijenjeni. Promijenite ih ondje prema svom instrumentu.

## Stvarna ruka
> [!CAUTION]
> Još nije testirano. Ovi koraci slijede AgileX dokumentaciju. Ne ulazite u doseg ruke dok se pomiče i držite tipku za zaustavljanje u nuždi pri ruci.

Spojite Piperov USB-CAN adapter na računalo. Unutar kontejnera podignite CAN sučelje:
```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts
bash can_activate.sh
```
Ovo podiže `can0` na 1 000 000 bit/s. Provjerite komunicira li ruka:
```bash
ip -details link show can0     # state UP, bitrate 1000000
candump can0                   # okviri prolaze dok je ruka uključena
```

Pokrenite upravljački program i najprije samo promatrajte stvarnu ruku u RVizu (klizači je ne pomiču):
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper \
  follow:=true control:=false
```

Kad to radi, zaustavite ga s `Ctrl+c`. Pokrenite samo upravljački program, bez njegovog RViza, jer `run_davinci_piper` pokreće vlastiti RViz i model robota s adapterom:
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper
```
i u drugom terminalu (`./run_piper.sh`):
```bash
run_davinci_piper --rings --follow
```
S `--follow` RViz i SOFA prikazuju izmjerene položaje zglobova ruke, a tipke RUKE kreću od trenutne poze ruke. Upravljački program pomiče ruku u položaje koje tipke RUKE objavljuju na `control/joint_states`.

Vlastiti motori adaptera još nisu spojeni na ROS; tipke INSTRUMENTA pomiču instrument samo u simulaciji.

## Rad na vlastitom projektu
Sve datoteke nalaze se u mapi [docker](docker). Dockerfile ih kopira u sliku:

| Datoteka | U kontejneru | Što radi |
|---|---|---|
| [davinci/run_davinci_piper.sh](docker/davinci/run_davinci_piper.sh) | `run_davinci_piper` | pokreće tmux sesiju sa svim programima |
| [davinci/tile_windows.sh](docker/davinci/tile_windows.sh) | `/root/davinci_piper/` | otvara terminal s tipkama i razmješta prozore |
| [davinci/davinci_piper.launch.py](docker/davinci/davinci_piper.launch.py) | `/root/davinci_piper/` | ROS launch datoteka: model robota, RViz, upravljač za tipke RUKE ili klizači zglobova |
| [davinci/piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) | `/root/davinci_piper/` | model robota: Piper, adapter, instrument i okvir `instrument_wrist` koji SOFA prati |
| [davinci/piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py) | `/root/davinci_piper/` | tipke RUKE: pomiče vrh instrumenta, rješava inverznu kinematiku, objavljuje položaje zglobova |
| [davinci/piper_tool_bridge.py](docker/davinci/piper_tool_bridge.py) | `/root/davinci_piper/` | šalje SOFA-i pozu okvira `instrument_wrist` |
| [sofa/twist_socket_bridge.py](docker/sofa/twist_socket_bridge.py) | `/opt/sofa_teleop/` | šalje tipke INSTRUMENTA SOFA-i |
| [sofa/davinci_piper_teleop.py](docker/sofa/davinci_piper_teleop.py) | `/opt/sofa_teleop/` | strana SOFA-e: postavlja Piper u scenu i pomiče instrument |
| [sofa/sofa_env_sofa25.patch](docker/sofa/sofa_env_sofa25.patch) | primijenjen na `/opt/sofa_env` | prilagođava LapGym za SOFA v25.12 i dodaje zglob instrumenta i neovisne čeljusti |
| [sofa/lapgym_keyboard_teleop.py](docker/sofa/lapgym_keyboard_teleop.py), [sofa/run_sofa_teleop.sh](docker/sofa/run_sofa_teleop.sh) | `run_sofa_teleop` | LapGymova vlastita hvataljka na sceni s organom, upravljana tipkovnicom, bez Pipera |
| [sofa/smoke_test.py](docker/sofa/smoke_test.py) | `/opt/sofa_teleop/` | učitava svih 14 LapGym scena i u svakoj izvodi nekoliko koraka |
| [sofa/sofa-python](docker/sofa/sofa-python) | `sofa-python` | Python sa SOFA-om i LapGymom; koristite ga za pokretanje SOFA skripti |

SOFA skripte pokreću se sa `sofa-python` (Python 3.12 u vlastitom okruženju), a ne sa sustavskim `python3` koji koristi ROS. Provjerite učitavaju li se sve scene:
```bash
sofa-python /opt/sofa_teleop/smoke_test.py
```

Dvije UDP poruke koje SOFA prima na portu 5006 su u JSON formatu:
```
{"tool_pose": [x, y, z, qx, qy, qz, qw]}     poza okvira instrument_wrist u baznom okviru Pipera, metri
{"vel": [vx, vy, vz, wx, wy, wz]}            tipke INSTRUMENTA (geometry_msgs/Twist)
```
Za pomicanje vrha instrumenta iz vlastitog programa objavite `geometry_msgs/Twist` na `/piper/cmd_vel`, istu poruku koju šalju tipke RUKE. `linear` pomiče vrh u baznom okviru Pipera, a `angular.z` okreće instrument; vrijednost 0.5 za `linear` (1.0 za `angular.z`) daje punu brzinu od 40 mm/s (0.25 rad/s).

Promjene koje napravite unutar kontejnera gube se kad ga uklonite (`docker rm -f piper-jazzy`). Umjesto toga mijenjajte datoteke u mapi `docker` i ponovno izgradite sliku, ili kopirajte promijenjenu datoteku naredbom `docker cp <datoteka> piper-jazzy:<putanja>`.


## Licenca
Kod u ovom repozitoriju je pod [MIT licencom](LICENSE). CAD model adaptera, koji Docker izgradnja preuzima, je pod GPL-3.0 (vidi njegov repozitorij).

[^1]: AgileX Piper: ruka sa 6 zglobova kojom se upravlja preko CAN-a. ROS 2 upravljački program je [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2), grana `ros2`, s Python SDK-om [pyAgxArm](https://github.com/agilexrobotics/pyAgxArm).
[^2]: [Open-Platform adaptor for da Vinci Si instruments](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Njegov CAD model (GPL-3.0) preuzima se tijekom Docker izgradnje i nije spremljen u ovom repozitoriju.
[^3]: [sofa_env](https://github.com/ScheiklP/sofa_env), autori Paul Maria Scheikl i suradnici, LapGym zbirka kirurških scena za SOFA-u (MIT licenca). Ovaj repozitorij sadrži samo zakrpu (patch) za nju; izgradnja preuzima original.
