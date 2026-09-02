# Wallpaper Workflow

This document explains how wallpaper storage, selection, synchronization, and reload daemons are organized.

---

## Architecture Flow

```text
[ User presses Super + Shift + W ]
              │
              ▼
   [ hypr/scripts/wallpaper.sh ]
              │
    ┌─────────┴────────────────────────┐
    ▼                                  ▼
[ hypr/hyprpaper.conf ]       [ hypr/hyprlock.conf ]
  path = $WALLPAPER             path = $WALLPAPER
    │                                  │
    ▼                                  ▼
Restart hyprpaper             Synchronized lock screen
```

---

## Wallpaper Storage

* All wallpaper assets live in `~/.config/hypr/hyprpaper/`.
* Supported image formats include `.png`, `.jpg`, `.jpeg`, and `.webp`.
* Wallpapers are rendered using `fit_mode = cover` so aspect ratios fill display outputs cleanly.

---

## Multi-Daemon Synchronization

A common issue in Wayland desktop environments is visual desynchronization between the desktop wallpaper and the lockscreen wallpaper. The `wallpaper.sh` script resolves this by updating both configuration files simultaneously:

1. Selects an image at random from `~/.config/hypr/hyprpaper/`.
2. Updates `hypr/hyprpaper.conf`:
   ```bash
   sed -i -E "s|path = .*|path = $WALLPAPER|g" "$HYPRPAPER_CONF"
   ```
3. Updates `hypr/hyprlock.conf`:
   ```bash
   sed -i -E "s|path = .*|path = $WALLPAPER|g" "$HYPRLOCK_CONF"
   ```
4. Restarts `hyprpaper` to apply the wallpaper immediately:
   ```bash
   killall hyprpaper
   hyprpaper >/dev/null 2>&1 &
   ```

Because `hyprlock.conf` now references the same image path, activating the screen lock (`Super + L`) displays the exact same wallpaper with Gaussian blur applied.

---

## Adding Custom Wallpapers

To add your own wallpapers to the rotation:
1. Copy image files into `~/.config/hypr/hyprpaper/`.
2. Press `Super + Shift + W` to trigger the shuffler script.

---

## Related Documents

* [Hyprpaper Component Reference](../components/hyprpaper.md)
* [Hyprlock Component Reference](../components/hyprlock.md)
* [Keybindings Reference](keybindings.md)
