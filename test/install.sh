#!/usr/bin/env bash
# Installs the test tools from this folder into a piper-jazzy container: run_davinci_piper (the Piper
# driving the instrument in SOFA), the pose bridge, the SOFA scene that follows the Piper, the
# keyboard jog, and xterm / wmctrl / xprop for arranging the windows.
#
# On the host:            test/install.sh [container]      (default container: piper-jazzy)
# Inside a container:     bash install.sh                  (run from this folder)
#
# The files are copied into the container, so they are lost when the container is removed.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -d /root/davinci_piper ]; then  # on the host: copy this folder in and run there
    CONTAINER=${1:-piper-jazzy}
    docker exec "$CONTAINER" rm -rf /tmp/piper_test
    docker cp "$HERE" "$CONTAINER":/tmp/piper_test
    exec docker exec "$CONTAINER" bash /tmp/piper_test/install.sh
fi

install -m 755 "$HERE"/run_davinci_piper.sh "$HERE"/tile_windows.sh \
    "$HERE"/piper_tool_bridge.py "$HERE"/piper_cartesian_jog.py /root/davinci_piper/
install -m 644 "$HERE"/davinci_piper_teleop.py /opt/sofa_teleop/
ln -sf /root/davinci_piper/run_davinci_piper.sh /usr/local/bin/run_davinci_piper
if ! command -v xterm > /dev/null || ! command -v wmctrl > /dev/null || ! command -v xprop > /dev/null; then
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends xterm wmctrl x11-utils > /dev/null
fi
echo "Installed run_davinci_piper; start it with:  run_davinci_piper --rings"
