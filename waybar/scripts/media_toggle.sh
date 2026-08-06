#!/bin/bash
if pgrep -f media_popup.py > /dev/null; then
    pkill -f media_popup.py
else
    python3 ~/.config/waybar/scripts/media_popup.py &
fi
