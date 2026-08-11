-- Monitor configuration.
--
-- An empty `output` string tells Hyprland to apply the rule to every detected
-- output, mirroring the documented fallback in the example config. This keeps
-- the baseline safe on arbitrary laptops without hardcoding vendor names like
-- "eDP-1". Per-output overrides belong in a future hardware-specific module.
--
-- Reference: https://wiki.hypr.land/Configuring/Basics/Monitors/
hl.monitor({
    output   = "",
    mode     = "1920x1080@60.05600",  -- let the monitor advertise its 'preferred' mode
    position = "auto",       -- arrange outputs automatically
    scale    = "1.25",       -- pick a sane HiDPI scale per output
})
