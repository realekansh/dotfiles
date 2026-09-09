#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Hyprsunset Night Light Toggle Script
#
# Toggles the Hyprsunset color temperature between warm night mode (default: 4000K)
# and daytime neutral identity matrix.
#
# Ensures the hyprsunset daemon is active, checks state in $XDG_RUNTIME_DIR,
# and issues an IPC call via `hyprctl hyprsunset`.
#
# Triggered anytime via SUPER + SHIFT + N or clickable Waybar modules.
# -----------------------------------------------------------------------------
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
