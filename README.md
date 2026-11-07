Kliknite u gornji desni kut za sadržaj ↗️ | [English version](README_en.md)

# Piper da Vinci simulacija
Ove upute opisuju kako postaviti sve što je potrebno za upravljanje kirurškim instrumentom da Vinci koji drži robotska ruka AgileX Piper. Najprije se radi u simulaciji, a kasnije na stvarnoj ruci.

> [!NOTE]
> Ako tijekom instalacije naiđete na grešku ili problem, najprije pogledajte karticu [Issues](../../issues); možda je problem već riješen. Ako nije, otvorite novi issue.

## Uvod
Robot je AgileX Piper, mala ruka sa 6 zglobova[^1]. Na njezinoj prirubnici nalazi se otvoreni adapter za da Vinci Si instrumente[^2] koji drži 8 mm da Vinci Si instrument (EndoWrist). Motori adaptera okreću četiri ulazna diska instrumenta. Njima se upravlja rotacijom instrumenta oko osovine (roll), pitchem zgloba i svakom čeljusti zasebno. Kad se obje čeljusti okreću u istu stranu, to je yaw zgloba, a kad se okreću jedna od druge, hvataljka se otvara ili zatvara. Ukratko, ruka određuje gdje je instrument i kamo mu je usmjerena osovina, a adapter određuje što radi vrh instrumenta.

Simulacija se sastoji od dva dijela. Prvi je ROS 2 Jazzy sa službenim AgileX upravljačkim programom [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2), a RViz prikazuje Piper s adapterom i instrumentom. Drugi je simulator SOFA v25.12 s dvije kirurške scene za vježbu iz zbirke [LapGym](https://github.com/ScheiklP/sofa_env)[^3]. U sceni s prstenovima (pick_and_place) treba podignuti prsten i staviti ga na stup iste boje, a u sceni s organom (grasp_lift_touch) treba uhvatiti žučni mjehur i podignuti ga. Instrument u tim scenama ima iste stupnjeve slobode kao adapter: roll, pitch zgloba i dvije neovisne čeljusti.

Simulacijom se upravlja s dvije tipkovnice u jednom terminalu. Tipke ruke (ARM keys) pomiču vrh instrumenta preko Pipera, a tipke instrumenta (INSTRUMENT keys) upravljaju adapterom. Dijelovi su povezani ovako:

```
ARM keys ──/piper/cmd_vel──> piper_cartesian_jog ──control/joint_states──> robot_state_publisher ──TF──> piper_tool_bridge ──UDP──> SOFA
                             (inverzna kinematika)                         (RViz prikazuje ruku)         (poza instrumenta)

INSTRUMENT keys ──/davinci/cmd_vel──> twist_socket_bridge ──UDP──> SOFA (roll, pitch zgloba, yaw zgloba, hvat)
```

SOFA radi u vlastitom Python okruženju, pa s ROS-om komunicira UDP porukama na istom računalu (port 5006), a ne preko ROS topica. Na stvarnoj ruci AgileX upravljački program čita isti topic `control/joint_states` i pomiče ruku u zadane položaje zglobova.

> [!IMPORTANT]
> Sve u ovom repozitoriju testirano je samo u simulaciji. Upravljanje stvarnim Piperom ovim programima još nije testirano. Prije toga pročitajte odjeljak [Stvarna ruka](#stvarna-ruka).

## Prijava problema
Ako naiđete na grešku koju ne možete sami riješiti ili zapnete na nekom koraku, otvorite [Issue](../../issues) u ovom repozitoriju. Navedite operacijski sustav i način instalacije, opišite problem i priložite cijeli ispis naredbe koja je dovela do greške. Tako ćete najbrže dobiti odgovor, a pomoći ćete i drugima koji kasnije naiđu na istu grešku.

## Instalacija
Računalo možete pripremiti na dva načina:

1. **Pomoću Dockera** (preporučeno) - ROS 2, upravljački program za Piper, SOFA, LapGym i ostali paketi instalirani su u slici i spremni za korištenje.
2. Ako već imate Ubuntu 24.04 s **ROS 2 Jazzy**, sve možete instalirati i ručno.

### 1) Instalacija s Dockerom (preporučeno)
Ukratko, Docker je alat koji u jedan kontejner pakira sve što je potrebno za određenu aplikaciju. Možete ga zamisliti kao lagani virtualni stroj koji radi na vašem računalu. Više informacija nalazi se na [službenoj stranici](https://www.docker.com/). Docker se ovdje koristi jer ROS 2 Jazzy treba Ubuntu 24.04, a SOFA i LapGym trebaju točno određene verzije Python paketa, pa je najjednostavnije da svi koriste istu sliku.

#### Preduvjeti
Potreban vam je Linux s grafičkim sučeljem (X11 ili Wayland) i oko 12 GB slobodnog prostora na disku, jer slika ima oko 9 GB. Postavka je testirana na Ubuntu 22.04 s GNOME-om na Waylandu i integriranom AMD grafikom, koju kontejner koristi preko `/dev/dri`. Intel grafika trebala bi raditi na isti način. NVIDIA grafika nije testirana; za nju je potreban [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) i dodatne opcije za `docker run`.

#### Upute korak po korak
Slijedite ove [upute](https://docs.docker.com/engine/install/ubuntu/) za instalaciju Docker enginea.

Zatim slijedite ove [neobavezne korake](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) kako biste Docker mogli koristiti bez root ovlasti. Ako to preskočite, svaku `docker` naredbu morat ćete pokretati sa `sudo`.

Sada pripremite Docker sliku koja se koristi za simulaciju. Klonirajte ovaj repozitorij u svoj home ili neki drugi direktorij i uđite u mapu `docker`.
```bash
git clone https://github.com/AntonioSkara132/piper_davinci_simulation.git
cd piper_davinci_simulation/docker
```

Izgradite Docker sliku. Vidjet ćete puno ispisa. Prva izgradnja preuzima nekoliko GB (ROS 2, SOFA, Python paketi), pa traje neko vrijeme. Pričekajte da završi.
```bash
docker build -t piper-jazzy .
```

Kad imate sliku, potreban vam je kontejner. Skripta `run_piper.sh` ga stvara pri prvom pokretanju i otvara ljusku u njemu.
```bash
./run_piper.sh
```

Kad skripta završi, odzivnik u terminalu trebao bi se promijeniti iz
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
> - Izlaz iz kontejnera - `Ctrl+d`. Kontejner nastavlja raditi u pozadini.
> - Novi terminal u istom kontejneru - ponovno pokrenite `./run_piper.sh` u drugom prozoru terminala.
> - Jedna naredba u kontejneru iz vašeg terminala - `./run_piper.sh <naredba>`
> - Zaustavljanje kontejnera - `docker stop piper-jazzy`
> - Brisanje kontejnera (gube se sve promjene napravljene unutar njega) - `docker rm -f piper-jazzy`
> - Nakon ponovne izgradnje slike - `docker rm -f piper-jazzy`, zatim `./run_piper.sh`, kako bi se kontejner napravio iz nove slike.

Skripta `run_piper.sh` pokreće kontejner s nekoliko opcija. Naredba `xhost +local:` dopušta kontejneru da otvara prozore na vašoj radnoj površini, a `DISPLAY` i `/tmp/.X11-unix` služe istoj svrsi. `--device /dev/dri` daje RViz-u i SOFA-i hardverski OpenGL. Zbog `--net=host` ROS 2 topici iz kontejnera vidljivi su na vašem računalu i kontejner može koristiti CAN sučelje stvarne ruke, a `--privileged` je potreban da bi se to sučelje podiglo iznutra kontejnera.

> [!WARNING]
> `xhost +local:` dopušta programima svih lokalnih korisnika da crtaju po vašem zaslonu dok se ne odjavite. Na zajedničkom računalu to poništite naredbom `xhost -local:` kad završite.
>
> Zbog `--net=host` svi na istoj mreži s istim `ROS_DOMAIN_ID` međusobno vide ROS topice. Ako u laboratoriju radi više ljudi, neka svako računalo ima svoj broj, na primjer `export ROS_DOMAIN_ID=17` (bilo koji broj od 0 do 101).

Naredbi `docker build` možete dodati i opcije. `--build-arg WITH_SOFA=false` izostavlja SOFA-u i simulaciju (slika je oko 3 GB manja). `--build-arg WITH_MOVEIT=true` dodatno instalira MoveIt i gradi `agx_arm_moveit` (nekoliko GB više). `--build-arg AGX_ARM_ROS_REF=ros2 --build-arg PYAGXARM_REF=main` instalira najnoviji upravljački program i SDK za Piper umjesto testiranih verzija.

### 2) Ručna instalacija (ako već imate ROS 2)
> Pretpostavlja se da imate Ubuntu 24.04 s ROS 2 Jazzy.

Testirana je samo instalacija s Dockerom, pa je preporučujemo i ako već imate ROS. Ako ipak želite instalirati izravno na sustav, [Dockerfile](docker/Dockerfile) navodi sve korake redom. Skripte očekuju iste putanje kao u slici: `/opt/sofa`, `/opt/sofa_venv`, `/opt/sofa_env`, `/opt/sofa_teleop` i `/root/davinci_piper`.

## Provjera instalacije na primjeru
Sada kad je simulacija spremna, možete pokušati pomaknuti instrument. Scenu s prstenovima pokrećete unutar kontejnera naredbom
```bash
run_davinci_piper --rings
```
ili iz vlastitog terminala, u mapi `docker`:
```bash
./run_piper.sh run_davinci_piper --rings
```

Nakon nekoliko sekundi otvaraju se tri prozora koji ispunjavaju zaslon: SOFA sa scenom lijevo, RViz s Piperom gore desno i terminal s tipkama dolje desno.

```
+--------------+------------------+
|              |      RViz        |
|     SOFA     | (Piper + alat)   |
|   prstenovi  +------------------+
|              | terminal s tipk. |
+--------------+------------------+
```

Terminal s tipkama podijeljen je na tri okna, a tipkate u onom na koje kliknete. U prvom oknu su poruke iz SOFA-e. Svakih 5 sekundi ondje se ispisuje statusna linija s položajem zgloba instrumenta u milimetrima, kutovima rolla, pitcha, yawa i hvata te podatkom je li nešto uhvaćeno. Drugo okno (ARM keys) pomiče vrh instrumenta preko Pipera, a treće (INSTRUMENT keys) upravlja adapterom.

Tipke u oba okna raspoređene su kao u paketu `teleop_twist_keyboard`:

| Tipka | ARM keys (okno 2) | INSTRUMENT keys (okno 3) |
|---|---|---|
| `i` / `,` | vrh naprijed / natrag (od vas / prema vama u prikazu SOFA-e) | pitch zgloba |
| `J` / `L` (sa `Shift`) | vrh lijevo / desno | zatvaranje / otvaranje čeljusti |
| `t` / `b` | vrh gore / dolje | yaw zgloba (obje čeljusti zajedno) |
| `j` / `l` | okretanje instrumenta oko okomite osi kroz vrh | roll instrumenta oko osovine |
| `k` | stop | stop |

Pritisnuta tipka nastavlja pomak dok ne pritisnete `k` ili neku drugu tipku, pa je ne morate držati. Tipkama `q` i `z` ubrzavate i usporavate tu tipkovnicu.

U prvom oknu možete upisati `a` i `Enter` za ponovno sidrenje. Instrument tada ostaje gdje jest u sceni, a trenutna poza Pipera postaje nova referenca, slično papučici spojke (clutch) na da Vinci konzoli. `r` i `Enter` ponovno pokreću scenu. U prozoru SOFA-e kotačićem miša zumirate, povlačenjem lijevom tipkom okrećete pogled, povlačenjem desnom tipkom ga pomičete, a tipkom `c` vraćate početni pogled.

Za vježbu pokušajte podići prsten. Odmah nakon pokretanja (ili nakon `r` + `Enter`) zglob instrumenta je na otprilike (0, 65, 20) mm, a čeljusti su otvorene.

1. U oknu ARM keys pritisnite `J`, nakon otprilike pola sekunde `k`, zatim `,` i nakon pola sekunde opet `k`. Zglob bi trebao biti na otprilike (26, 65, -3) mm, s čeljustima iznad bližeg ruba prstena.
2. Pritisnite `b` i spuštajte zglob dok ne bude na visini od otprilike 27 mm.
3. U oknu INSTRUMENT keys pritisnite `J` i zatvarajte čeljusti dok statusna linija ne pokaže `grasped`.
4. U oknu ARM keys pritisnite `t` da podignete prsten.

Program ima još nekoliko opcija. Bez `--rings` pokreće se scena s organom. S `--sliders` rukom se upravlja klizačem za svaki zglob umjesto tipkama. `--follow` služi za stvarnu ruku (vidi [Stvarna ruka](#stvarna-ruka)). `--no-tile` ne otvara terminal s tipkama i ne razmješta prozore, a na sesiju se tada spajate s `tmux attach -t davinci_piper`. `--motion-scale 0.5` znači da se instrument u sceni pomiče upola manje od ruke.

Sve radi u tmux sesiji `davinci_piper`. U njezinom drugom prozoru (`Ctrl+b`, zatim `n`) vide se ROS programi. Sve zaustavljate naredbom
```bash
tmux kill-session -t davinci_piper
```

Nekoliko poveznica o tmuxu: [Getting started with Tmux](https://linuxize.com/post/getting-started-with-tmux/), [Tmux Cheat Sheet](https://tmuxcheatsheet.com/)

### Napomene
Doseg ruke je malen. Iz početne poze vrh doseže otprilike 240 mm naprijed, 115 mm natrag, 80 mm lijevo, 120 mm desno, 95 mm gore i 200 mm dolje, a instrument se okreće samo oko 9 stupnjeva na svaku stranu. Kad bi tipka odvela ruku preko granice nekog zgloba, ruka stane, a u ROS prozoru (`Ctrl+b`, `n`) ispiše se `Arm cannot move further this way`. Tada pritisnite suprotnu tipku.

Čeljusti nisu točno ispod zgloba. Piper drži instrument nagnut, s osovinom oko 23 stupnja od okomice, pa su čeljusti oko 9 mm ispred položaja zgloba iz statusne linije i oko 22 mm ispod njega.

Prsten se uhvati samo kad ga dodiruju obje čeljusti. Ako su čeljusti nekoliko milimetara previsoko ili sa strane, zatvore se do kraja (hvat 0) i ništa ne uhvate. Tada ih otvorite, pomaknite instrument i pokušajte ponovno. Roll držite blizu 0 kako bi se čeljusti zatvarale poprijeko prstena, a ne uzduž njega.

Uhvaćeni prsten visi s čeljusti i njiše se oko točke hvata. Scena prsten smatra postavljenim tek kad leži ravno oko stupa, a ako ga spustite ravno na stup, ostat će visjeti preko vrha. Bolje je spustiti donji rub prstena na podlogu oko 20 mm prije stupa, pomaknuti instrument naprijed preko stupa tako da se prsten prevrne i legne oko njega, i tek onda otvoriti čeljusti.

U simulaciji nema troakara. U stvarnoj operaciji osovina prolazi kroz otvor u trbušnoj stijenci, a ovdje se slobodno pomiče.

Model adaptera napravljen je iz njegovih CAD datoteka, ali dimenzije kućišta i osovine instrumenta u [piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) su procijenjene. Ako imate drugačiji instrument, promijenite ih ondje.

## Stvarna ruka
> [!CAUTION]
> Ovo još nije testirano. Koraci slijede AgileX dokumentaciju. Dok se ruka pomiče, ne ulazite u njezin doseg i držite tipku za zaustavljanje u nuždi pri ruci.

Spojite Piperov USB-CAN adapter na računalo i unutar kontejnera podignite CAN sučelje.
```bash
cd ~/agx_arm_ws/src/agx_arm_ros/scripts
bash can_activate.sh
```
Skripta podiže `can0` na 1 000 000 bit/s. Provjerite komunicira li ruka:
```bash
ip -details link show can0     # state UP, bitrate 1000000
candump can0                   # okviri prolaze dok je ruka uključena
```

Pokrenite upravljački program i najprije samo promatrajte stvarnu ruku u RViz-u (klizači je ne pomiču).
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm_rviz.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper \
  follow:=true control:=false
```

Kad to radi, zaustavite ga s `Ctrl+c`. Zatim pokrenite samo upravljački program, bez njegovog RViz-a, jer `run_davinci_piper` pokreće vlastiti RViz i model robota s adapterom:
```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
  can_port:=can0 arm_type:=piper effector_type:=agx_gripper
```
a u drugom terminalu (`./run_piper.sh`) pokrenite
```bash
run_davinci_piper --rings --follow
```
S opcijom `--follow` RViz i SOFA prikazuju izmjerene položaje zglobova ruke, a tipke ruke kreću od njezine trenutne poze. Upravljački program pomiče ruku u položaje koje tipke ruke objavljuju na `control/joint_states`.

Motori adaptera još nisu spojeni na ROS, pa tipke instrumenta pomiču instrument samo u simulaciji.

## Rad na vlastitom projektu
Sve datoteke nalaze se u mapi [docker](docker), a Dockerfile ih kopira u sliku.

| Datoteka | U kontejneru | Što radi |
|---|---|---|
| [davinci/run_davinci_piper.sh](docker/davinci/run_davinci_piper.sh) | `run_davinci_piper` | pokreće tmux sesiju sa svim programima |
| [davinci/tile_windows.sh](docker/davinci/tile_windows.sh) | `/root/davinci_piper/` | otvara terminal s tipkama i razmješta prozore |
| [davinci/davinci_piper.launch.py](docker/davinci/davinci_piper.launch.py) | `/root/davinci_piper/` | ROS launch datoteka: model robota, RViz, upravljanje tipkama ili klizači zglobova |
| [davinci/piper_davinci.urdf.xacro](docker/davinci/piper_davinci.urdf.xacro) | `/root/davinci_piper/` | model robota: Piper, adapter, instrument i okvir `instrument_wrist` koji SOFA prati |
| [davinci/piper_cartesian_jog.py](docker/davinci/piper_cartesian_jog.py) | `/root/davinci_piper/` | tipke ruke: pomiče vrh instrumenta, rješava inverznu kinematiku i objavljuje položaje zglobova |
| [davinci/piper_tool_bridge.py](docker/davinci/piper_tool_bridge.py) | `/root/davinci_piper/` | šalje SOFA-i pozu okvira `instrument_wrist` |
| [sofa/twist_socket_bridge.py](docker/sofa/twist_socket_bridge.py) | `/opt/sofa_teleop/` | šalje SOFA-i tipke instrumenta |
| [sofa/davinci_piper_teleop.py](docker/sofa/davinci_piper_teleop.py) | `/opt/sofa_teleop/` | strana SOFA-e: postavlja Piper u scenu i pomiče instrument |
| [sofa/sofa_env_sofa25.patch](docker/sofa/sofa_env_sofa25.patch) | primijenjen na `/opt/sofa_env` | prilagođava LapGym za SOFA v25.12 i dodaje zglob instrumenta i neovisne čeljusti |
| [sofa/lapgym_keyboard_teleop.py](docker/sofa/lapgym_keyboard_teleop.py), [sofa/run_sofa_teleop.sh](docker/sofa/run_sofa_teleop.sh) | `run_sofa_teleop` | LapGymova hvataljka na sceni s organom, upravljana tipkovnicom, bez Pipera |
| [sofa/smoke_test.py](docker/sofa/smoke_test.py) | `/opt/sofa_teleop/` | učitava svih 14 LapGym scena i u svakoj izvodi nekoliko koraka |
| [sofa/sofa-python](docker/sofa/sofa-python) | `sofa-python` | Python sa SOFA-om i LapGymom, za pokretanje SOFA skripti |

SOFA skripte pokreću se sa `sofa-python` (Python 3.12 u zasebnom okruženju), a ne sa sustavskim `python3` koji koristi ROS. Učitavaju li se sve scene, provjerite naredbom
```bash
sofa-python /opt/sofa_teleop/smoke_test.py
```

SOFA na portu 5006 prima dvije vrste UDP poruka u JSON formatu:
```
{"tool_pose": [x, y, z, qx, qy, qz, qw]}     poza okvira instrument_wrist u baznom okviru Pipera, u metrima
{"vel": [vx, vy, vz, wx, wy, wz]}            tipke instrumenta (geometry_msgs/Twist)
```
Ako vrh instrumenta želite pomicati iz vlastitog programa, objavljujte poruku [geometry_msgs/Twist](https://docs.ros2.org/latest/api/geometry_msgs/msg/Twist.html) na topic `/piper/cmd_vel`, istu koju šalju tipke ruke. `linear` pomiče vrh u baznom okviru Pipera, a `angular.z` okreće instrument. Vrijednost 0.5 u `linear` daje punu brzinu od 40 mm/s, a 1.0 u `angular.z` punu brzinu okretanja od 0.25 rad/s.

Promjene napravljene unutar kontejnera gube se kad ga obrišete (`docker rm -f piper-jazzy`). Zato mijenjajte datoteke u mapi `docker` i ponovno izgradite sliku, ili pojedinu promijenjenu datoteku kopirajte u kontejner naredbom `docker cp <datoteka> piper-jazzy:<putanja>`.


## Licenca
Kod u ovom repozitoriju je pod [MIT licencom](LICENSE). CAD model adaptera, koji se preuzima tijekom izgradnje Docker slike, je pod licencom GPL-3.0 (vidi njegov repozitorij).

[^1]: AgileX Piper je ruka sa 6 zglobova kojom se upravlja preko CAN sabirnice. ROS 2 upravljački program je [agx_arm_ros](https://github.com/agilexrobotics/agx_arm_ros/tree/ros2), grana `ros2`, s Python SDK-om [pyAgxArm](https://github.com/agilexrobotics/pyAgxArm).
[^2]: [Open-Platform adaptor for da Vinci Si instruments](https://github.com/Manaf2584/Open-Platform-adaptor-for-da-vinci-si-instruments). Njegov CAD model (GPL-3.0) preuzima se tijekom izgradnje Docker slike i nije spremljen u ovom repozitoriju.
[^3]: [sofa_env](https://github.com/ScheiklP/sofa_env), autori Paul Maria Scheikl i suradnici, zbirka kirurških scena LapGym za SOFA-u (MIT licenca). Ovaj repozitorij sadrži samo zakrpu (patch) za nju, a original se preuzima tijekom izgradnje.
