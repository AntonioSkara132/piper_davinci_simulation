# Testni alati

Ova mapa nije u Docker slici. Služi za testiranje nakon promjena.

- `piper_cartesian_jog.py`: testni teleop. Iz poruka `Twist` na `/piper/cmd_vel` inverznom kinematikom računa položaje zglobova ruke, a iz `/davinci/cmd_vel` položaje zglobova adaptera, i sve objavljuje na `/control/joint_states`. Pokreće se s `run_davinci_piper --jog`.
- `moves.py`: unaprijed zadani pokreti preko `/piper/cmd_vel` i `/davinci/cmd_vel` (npr. `python3 moves.py grasp` uhvati prsten u sceni s prstenovima).
- `install.sh`: kopira `piper_cartesian_jog.py` u kontejner.
- `run_tests.sh`: provjerava sve načine rada `run_davinci_piper`, obje scene, svih 14 LapGym scena, `run_sofa_teleop` i model sa sliderima te ispisuje PASS ili FAIL za svaku provjeru.

## Instalacija u kontejner
Iz korijena repozitorija na računalu, dok kontejner `piper-jazzy` radi:
```bash
test/install.sh
docker exec -it piper-jazzy bash -ic 'run_davinci_piper --rings --jog'
```
Datoteka se kopira u kontejner, pa nestaje kad se kontejner obriše.

Tipke s `--jog` (okno ARM keys) i tipke instrumenta (okno INSTRUMENT keys):

| Tipka | ARM keys | INSTRUMENT keys |
|---|---|---|
| `i` / `,` | vrh naprijed / natrag | pitch zgloba |
| `J` / `L` | vrh lijevo / desno | zatvaranje / otvaranje čeljusti |
| `t` / `b` | vrh gore / dolje | yaw zgloba |
| `j` / `l` | okretanje oko okomite osi | roll |
| `k` | stop | stop |

U oknu SOFA-e `r` + `Enter` ponovno pokreće scenu. Zaustavljanje: `tmux kill-session -t davinci_piper`.

## Pokretanje testova
Testovi rade u zasebnom kontejneru s virtualnim zaslonom (Xvfb), pa ne otvaraju prozore na vašem računalu. Iz korijena repozitorija:
```bash
docker run -d --name piper-test -e ROS_DOMAIN_ID=55 -v "$PWD/test:/tmp/t2" piper-jazzy sleep infinity
docker exec piper-test bash -c 'apt-get update && apt-get install -y xvfb openbox ffmpeg'
docker exec -d piper-test bash -c 'Xvfb :99 -screen 0 1920x1080x24'
docker exec -d -e DISPLAY=:99 piper-test openbox
docker exec piper-test bash /tmp/t2/run_tests.sh
docker cp piper-test:/tmp/shots ./shots      # snimke zaslona
docker rm -f piper-test
```
Sve traje desetak minuta. `ROS_DOMAIN_ID` odvaja testni kontejner od ROS čvorova u drugim kontejnerima na istom računalu.
