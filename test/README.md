# Testni alati

Ova mapa nije u Docker slici. Služi za provjeru da se scene mogu voditi rukom i za testiranje nakon promjena.

- `run_davinci_piper.sh`: naredba `run_davinci_piper`. Pokreće ruku (model sa sliderima ili `--jog`), SOFA scenu koja prati ruku i tipke instrumenta te slaže prozore. Opcije su opisane na vrhu datoteke (`--rings`, `--jog`, `--no-arm`, `--follow`, `--no-tile`).
- `piper_tool_bridge.py`: čita TF `base_link` → `instrument_wrist` i šalje pozu SOFA-i preko UDP-a.
- `davinci_piper_teleop.py`: LapGym scena (organ ili prstenovi) u kojoj instrument prati primljenu pozu, a roll, zglob i hvat dolaze s tipkovnice.
- `tile_windows.sh`: slaže prozore SOFA-e, RViz-a, slidera i terminala.
- `piper_cartesian_jog.py`: testni teleop vrha instrumenta. Iz poruka `Twist` na `/piper/cmd_vel` inverznom kinematikom računa položaje zglobova i objavljuje ih na `/control/joint_states`.
- `moves.py`: unaprijed zadani pokreti preko `/piper/cmd_vel` i `/davinci/cmd_vel` (npr. `python3 moves.py grasp` uhvati prsten u sceni s prstenovima).
- `install.sh`: kopira gornje datoteke u kontejner i instalira xterm, wmctrl i xprop.
- `run_tests.sh`: provjerava sve načine rada `run_davinci_piper`, obje scene, svih 14 LapGym scena, `run_sofa_teleop` i model sa sliderima te ispisuje PASS ili FAIL za svaku provjeru.

## Instalacija u kontejner
Iz korijena repozitorija na računalu, dok kontejner `piper-jazzy` radi:
```bash
test/install.sh
docker exec -it piper-jazzy bash -ic 'run_davinci_piper --rings'          # slideri
docker exec -it piper-jazzy bash -ic 'run_davinci_piper --rings --jog'    # tipke za vrh instrumenta
```
Datoteke se kopiraju u kontejner, pa nestaju kad se kontejner obriše.

Tipke s `--jog` (okno ARM keys) i tipke instrumenta (okno INSTRUMENT keys):

| Tipka | ARM keys | INSTRUMENT keys |
|---|---|---|
| `i` / `,` | vrh naprijed / natrag | pitch zgloba |
| `J` / `L` | vrh lijevo / desno | zatvaranje / otvaranje čeljusti |
| `t` / `b` | vrh gore / dolje | yaw zgloba |
| `j` / `l` | okretanje oko okomite osi | roll |
| `k` | stop | stop |

U oknu SOFA-e `r` + `Enter` ponovno pokreće scenu, a `a` + `Enter` uzima trenutnu pozu ruke kao novu referencu. Zaustavljanje: `tmux kill-session -t davinci_piper`.

## Pokretanje testova
Testovi rade u zasebnom kontejneru s virtualnim zaslonom (Xvfb), pa ne otvaraju prozore na vašem računalu. Iz korijena repozitorija:
```bash
docker run -d --name piper-test -v "$PWD/test:/tmp/t2" piper-jazzy sleep infinity
docker exec piper-test bash -c 'apt-get update && apt-get install -y xvfb openbox ffmpeg'
docker exec -d piper-test bash -c 'Xvfb :99 -screen 0 1920x1080x24'
docker exec -d -e DISPLAY=:99 piper-test openbox
docker exec piper-test bash /tmp/t2/run_tests.sh
docker cp piper-test:/tmp/shots ./shots      # snimke zaslona
docker rm -f piper-test
```
Sve traje desetak minuta.
