#!/usr/bin/env bash

# The script uses playerctl --follow to stream metadata updates without polling
playerctl metadata --format '{{status}}'$'\t''{{playerName}}'$'\t''{{title}}'$'\t''{{artist}}' --follow | while IFS=$'\t' read -r status player title artist; do
  
  if [[ "$status" == "Stopped" || -z "$title" ]]; then
    # If no media is available, output empty string to hide the module
    echo '{"text": "", "class": "empty", "alt": "empty"}'
    continue
  fi
  
  if [[ -n "$artist" ]]; then
    text="$title - $artist"
  else
    text="$title"
  fi
  
  # Truncate gracefully if the text is too long
  if ((${#text} > 45)); then
    text="${text:0:42}..."
  fi
  
  # Escape quotes and backslashes for valid JSON
  text="${text//\\/\\\\}"
  text="${text//\"/\\\"}"
  
  # Extract base player name (e.g. firefox.instance123 -> firefox)
  player_base="${player%%.*}"
  
  # Note: Tooltip is completely disabled in media.jsonc
  echo "{\"text\": \"$text\", \"class\": \"${status,,}\", \"alt\": \"${player_base,,}\"}"
done
