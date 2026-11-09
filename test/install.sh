#!/usr/bin/env bash
# Installs the keyboard jog (piper_cartesian_jog.py) from this folder into a piper-jazzy container,
# for run_davinci_piper --jog.
#
# On the host:            test/install.sh [container]      (default container: piper-jazzy)
# Inside a container:     bash install.sh                  (run from this folder)
#
# The file is copied into the container, so it is lost when the container is removed.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -d /root/davinci_piper ]; then  # on the host: copy this folder in and run there
    CONTAINER=${1:-piper-jazzy}
    docker exec "$CONTAINER" rm -rf /tmp/piper_test
    docker cp "$HERE" "$CONTAINER":/tmp/piper_test
    exec docker exec "$CONTAINER" bash /tmp/piper_test/install.sh
fi

install -m 755 "$HERE"/piper_cartesian_jog.py /root/davinci_piper/
echo "Installed the jog; start it with:  run_davinci_piper --rings --jog"
