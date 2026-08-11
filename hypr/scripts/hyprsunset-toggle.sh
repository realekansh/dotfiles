#!/usr/bin/env bash

# Hyprsunset toggle script for Waybar / custom keybindings
# State file to track whether night mode is ON or OFF
STATE_FILE="${XDG_RUNTIME_DIR:-/tmp}/hyprsunset_state"
TEMP="${1:-4000}"

# Ensure hyprsunset daemon is running
if ! pgrep -x "hyprsunset" > /dev/null; then
    hyprsunset &
    # Allow a brief moment for the IPC socket to initialize
    sleep 0.3
fi

# Toggle logic
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" = "on" ]; then
    # Currently ON -> Turn OFF (reset to normal identity colors)
    hyprctl hyprsunset identity
    echo "off" > "$STATE_FILE"
    echo "Hyprsunset: Night mode OFF (Identity)"
else
    # Currently OFF -> Turn ON (apply night temperature)
    hyprctl hyprsunset temperature "$TEMP"
    echo "on" > "$STATE_FILE"
    echo "Hyprsunset: Night mode ON (${TEMP}K)"
fi
