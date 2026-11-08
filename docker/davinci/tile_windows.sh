#!/usr/bin/env bash
# Opens a terminal on the davinci_piper tmux session and tiles it with the SOFA, RViz and (in slider
# mode) joint slider windows so together they fill the screen:
#
#   +-------------+----------------+
#   |             |      RViz      |
#   |    SOFA     +----------------+
#   |             | [sliders] keys |
#   +-------------+----------------+
#
# Called by run_davinci_piper.sh; run it again to put the windows back if they were moved.
# Needs wmctrl and xterm (apt install wmctrl xterm). Works on X11 windows, which all of these are
# (they come from this container through XWayland on a Wayland desktop).
set -u
SESSION=davinci_piper
TERM_TITLE="Da Vinci Piper keys"

window_id() { wmctrl -l | awk -v t="$1" 'index($0, t) {print $1; exit}'; }

wait_for() {
    for _ in $(seq 120); do
        id=$(window_id "$1")
        [ -n "$id" ] && { echo "$id"; return 0; }
        sleep 0.5
    done
    echo "tile_windows: no window titled '$1' after 60 s" >&2
    return 1
}

# Usable area of the screen (without the top bar): "WA: x,y wxh"
read -r AX AY AW AH < <(wmctrl -d | awk '$2 == "*" {for (i = 1; i <= NF; i++) if ($i == "WA:") {split($(i+1), p, ","); split($(i+2), s, "x"); print p[1], p[2], s[1], s[2]}}')

if [ -z "$(window_id "$TERM_TITLE")" ]; then
    xterm -T "$TERM_TITLE" -fa Monospace -fs 10 -bg black -fg white -e tmux attach -t "$SESSION" &
fi

place() {  # window id, x, y, width, height (outer size, title bar and borders included)
    # wmctrl takes the frame position but the size of the window inside the frame, so subtract the
    # frame (_NET_FRAME_EXTENTS = left, right, top, bottom) from the size.
    local l r t b
    read -r l r t b < <(xprop -id "$1" _NET_FRAME_EXTENTS | awk -F' = ' '{gsub(",", ""); print $2}')
    wmctrl -i -r "$1" -b remove,maximized_vert,maximized_horz
    wmctrl -i -r "$1" -e "0,$2,$3,$(($4 - ${l:-0} - ${r:-0})),$(($5 - ${t:-0} - ${b:-0}))"
}

LEFT_W=$((AW / 2))
RIGHT_X=$((AX + LEFT_W))
RIGHT_W=$((AW - LEFT_W))
TOP_H=$((AH * 11 / 20))
BOTTOM_Y=$((AY + TOP_H))
BOTTOM_H=$((AH - TOP_H))

# The SOFA window is titled "LapGym grasp-lift-touch" or "LapGym pick-and-place".
sofa=$(wait_for "LapGym ") && place "$sofa" "$AX" "$AY" "$LEFT_W" "$AH"
rviz=$(wait_for " - RViz") && place "$rviz" "$RIGHT_X" "$AY" "$RIGHT_W" "$TOP_H"
keys=$(wait_for "$TERM_TITLE")
sliders=$(window_id "Joint State Publisher")
if [ -n "$sliders" ]; then
    SLIDERS_W=280
    place "$sliders" "$RIGHT_X" "$BOTTOM_Y" "$SLIDERS_W" "$BOTTOM_H"
    place "$keys" $((RIGHT_X + SLIDERS_W)) "$BOTTOM_Y" $((RIGHT_W - SLIDERS_W)) "$BOTTOM_H"
else
    place "$keys" "$RIGHT_X" "$BOTTOM_Y" "$RIGHT_W" "$BOTTOM_H"
fi
wmctrl -i -a "$keys"
