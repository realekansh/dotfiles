-- Keyboard and mouse bindings.
--
-- SUPER is the primary (and only) modifier for the baseline. Keeping a single
-- modifier avoids collisions with app-internal shortcuts (Ctrl/Alt) and leaves
-- SUPER+SHIFT and SUPER+CTRL as room to grow.
--
-- Kitty is the default terminal; this matches the planned desktop stack. No
-- bindings are created for applications outside this phase's scope (launcher,
-- file manager, screenshot tool, etc.) even if installed, per the Phase 1
-- contract.
--
-- Reference: https://wiki.hypr.land/Configuring/Basics/Binds/

local mainMod = "SUPER"
local terminal = "kitty"

-- Window lifecycle ----------------------------------------------------------

-- Launch a terminal.
hl.bind(mainMod .. " + Return", hl.dsp.exec_cmd(terminal))

-- Close the focused window.
hl.bind(mainMod .. " + W", hl.dsp.window.close())

-- Toggle floating on the focused window. (Avoids SUPER+V, which clashes with
-- "paste" muscle memory; "F" reads as "float" anyway.)
hl.bind(mainMod .. " + F", hl.dsp.window.float({ action = "toggle" }))

-- Fullscreen the focused window. Hyprland's fullscreen is a per-window toggle.
hl.bind(mainMod .. " + Space", hl.dsp.window.fullscreen({ action = "toggle" }))

-- Directional focus movement. Arrow keys are paired with Vim-style hjkl so the
-- scheme is usable on laptops without dedicated arrows and friendly to keyboard
-- users. Define the two sets once.
local focus_dirs = {
    { "left",  "left"  },
    { "right", "right" },
    { "up",    "up"    },
    { "down",  "down"  },
    { "left",  "h"     },
    { "right", "l"     },
    { "up",    "k"     },
    { "down",  "j"     },
}
for _, d in ipairs(focus_dirs) do
    hl.bind(mainMod .. " + " .. d[2], hl.dsp.focus({ direction = d[1] }))
end

-- Workspaces 1-10 -----------------------------------------------------------
--
-- Hyprland uses 1..10 as workspace IDs but maps workspace 10 onto the "0" key
-- on the keyboard, so the key index is `i % 10`.
for i = 1, 10 do
    local key = i % 10
    -- Switch to workspace.
    hl.bind(mainMod .. " + " .. key,                 hl.dsp.focus({ workspace = i }))
    -- Move the focused window to that workspace.
    hl.bind(mainMod .. " + SHIFT + " .. key,         hl.dsp.window.move({ workspace = i }))
end

-- Mouse ---------------------------------------------------------------------

-- Move a window by dragging with SUPER + left mouse button.
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })

-- Resize a window by dragging with SUPER + right mouse button.
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Cycle workspaces with the scroll wheel while holding SUPER.
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))
