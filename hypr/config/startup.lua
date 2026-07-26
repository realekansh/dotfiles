-- Session startup.
--
-- This module centralizes *all* `exec`-on-start commands. Phase 1 keeps this
-- intentionally minimal: no status bar, launcher, wallpaper daemon, lock
-- daemon, notification center, or polkit agent is started here. Those belong
-- to later phases once their own configuration exists and is ready to ship.
--
-- The only commands here wire the Wayland environment into the user's D-Bus
-- session so that XDG desktop portals, XWayland clients, and other autostarted
-- user services inherit a consistent environment. These are standard for any
-- Wayland compositor session and are not project-specific.
--
-- Commands are guarded with `command -v` so the config still loads cleanly on
-- systems where the helper is absent.

hl.on("hyprland.start", function ()
    -- Pull WAYLAND_DISPLAY / XDG_SESSION_TYPE and friends into the user D-Bus and
    -- systemd user session. Order is conventional: D-Bus first, then systemd.
    hl.exec_cmd("command -v dbus-update-activation-environment >/dev/null 2>&1 && dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("command -v systemctl >/dev/null 2>&1 && systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_CURRENT_SESSION")

    -- Start the status bar once Hyprland has exported the Wayland session.
    hl.exec_cmd("waybar")
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("kitty")
    hl.exec_cmd("dunst")
    hl.exec_cmd("vicinae server")
end)

