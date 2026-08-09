#!/usr/bin/env bash

curHost=$(cat "$HOME/.config/.secrets/hostname.txt")
cur=$(awk 'match($0,v){ print NR; exit }' v="$curHost" "$HOME/.config/.secrets/hostnames.txt")
new=$((cur + ${1:-1}))

lines=$(wc -l < "$HOME/.config/.secrets/hostnames.txt")
lines=$((lines + 1))
if [ "$new" -eq 0 ]; then
    new=$lines
elif [ "$new" -gt "$lines" ]; then
    new=1
fi

sed -n "${new}p" "$HOME/.config/.secrets/hostnames.txt" | tr -d '\n' > "$HOME/.config/.secrets/hostname.txt"