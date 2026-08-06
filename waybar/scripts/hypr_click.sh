#!/bin/bash
workspace="$1"
# For integers we can omit quotes, for strings we might need them, but hyprland lua accepts strings for integers too.
hyprctl dispatch "hl.dsp.focus({workspace = \"$workspace\"})"
