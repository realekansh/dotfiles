#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Wallpaper & Waybar Theme Shuffle Script
#
# Randomly selects a wallpaper from ~/.config/hypr/hyprpaper/ and a matching
# Waybar stylesheet from ~/.config/waybar/themes/.
#
# Updates hyprpaper.conf and hyprlock.conf for persistence across reboots,
# then smoothly refreshes the running hyprpaper daemon via Wayland IPC and
# signals Waybar to reload its styling.
#
# Triggered anytime via SUPER + SHIFT + W
# -----------------------------------------------------------------------------

WALLPAPER_DIR="$HOME/.config/hypr/hyprpaper"
THEME_DIR="$HOME/.config/waybar/themes"
WAYBAR_STYLE="$HOME/.config/waybar/style.css"
HYPRPAPER_CONF="$HOME/.config/hypr/hyprpaper.conf"
HYPRLOCK_CONF="$HOME/.config/hypr/hyprlock.conf"

# Pick a random supported wallpaper
WALLPAPER="$(
    find "$WALLPAPER_DIR" -maxdepth 1 -type f \
        \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) \
        | shuf -n 1
)"

if [[ -z "$WALLPAPER" ]]; then
    echo "No wallpapers found in $WALLPAPER_DIR"
    exit 1
fi

# Pick a random Waybar theme
THEME="$(
    find "$THEME_DIR" -maxdepth 1 -type f -name '*.css' \
        | shuf -n 1
)"

if [[ -z "$THEME" ]]; then
    echo "No themes found in $THEME_DIR"
    exit 1
fi

THEME_BASENAME=$(basename "$THEME")

echo "Setting wallpaper to: $WALLPAPER"
echo "Applying Waybar theme: $THEME_BASENAME"

# Update hyprpaper configuration
sed -i -E "s|path = .*|path = $WALLPAPER|g" "$HYPRPAPER_CONF"

# Update hyprlock configuration
sed -i -E "s|path = .*|path = $WALLPAPER|g" "$HYPRLOCK_CONF"

# Update Waybar theme
sed -i -E "s|@import url\(\"themes/[^\"]+\.css\"\);|@import url(\"themes/${THEME_BASENAME}\");|g" "$WAYBAR_STYLE"

# Reload hyprpaper dynamically if running, otherwise launch it
if pgrep -x hyprpaper >/dev/null; then
    hyprctl hyprpaper wallpaper ",$WALLPAPER"
else
    hyprpaper >/dev/null 2>&1 &
fi

# Reload waybar
killall -SIGUSR2 waybar

echo "Done! Configurations updated permanently."
