#!/usr/bin/env python3
import gi
gi.require_version("Playerctl", "2.0")
from gi.repository import Playerctl, GLib
import json
import sys

SCROLL_LIMIT = 40
SCROLL_SPEED = 0.25  # seconds

class Scroller:
    def __init__(self):
        self.manager = Playerctl.PlayerManager()
        self.manager.connect("name-appeared", self.on_player_appeared)
        self.manager.connect("player-vanished", self.on_player_vanished)
        
        self.active_player = None
        self.current_text = ""
        self.current_icon = ""
        self.current_class = "stopped"
        
        self.scroll_idx = 0
        self.scroll_text = ""
        self.is_playing = False
        
        self.icons = {
            "spotify": "",
            "mpv": "",
            "vlc": "󰕼",
            "firefox": "",
            "chromium": "",
            "youtube-music": "",
            "default": ""
        }
        
        for name in self.manager.props.player_names:
            self.init_player(name)
            
        GLib.timeout_add(int(SCROLL_SPEED * 1000), self.tick)
            
    def init_player(self, name):
        player = Playerctl.Player.new_from_name(name)
        player.connect("playback-status", self.on_status)
        player.connect("metadata", self.on_metadata)
        self.manager.manage_player(player)
        
    def on_player_appeared(self, manager, name):
        self.init_player(name)
        self.update_state()
        
    def on_player_vanished(self, manager, name):
        self.update_state()
        
    def update_state(self):
        players = self.manager.props.players
        if not players:
            self.active_player = None
            self.is_playing = False
            self.current_class = "stopped"
            self.scroll_text = ""
            self.output()
            return
            
        active = None
        for p in players:
            if p.props.playback_status == Playerctl.PlaybackStatus.PLAYING:
                active = p
                break
        if not active:
            for p in players:
                if p.props.playback_status == Playerctl.PlaybackStatus.PAUSED:
                    active = p
                    break
        if not active:
            active = players[0]
            
        self.active_player = active
        self.is_playing = (active.props.playback_status == Playerctl.PlaybackStatus.PLAYING)
        
        artist = active.get_artist() or ""
        title = active.get_title() or ""
        if artist and title:
            text = f"{title} - {artist}"
        else:
            text = title or artist or "Unknown"
            
        player_name = active.props.player_name.lower()
        self.current_class = "playing" if self.is_playing else "paused"
        
        if active.props.playback_status == Playerctl.PlaybackStatus.STOPPED:
            self.current_class = "stopped"
            text = ""
        
        icon = self.icons.get("default")
        for key in self.icons:
            if key in player_name:
                icon = self.icons[key]
                break
        self.current_icon = icon
        
        if text != self.scroll_text:
            self.scroll_text = text
            self.scroll_idx = 0
            
        self.output()
        
    def on_status(self, player, status):
        self.update_state()
        
    def on_metadata(self, player, metadata):
        self.update_state()
        
    def output(self):
        if not self.scroll_text or self.current_class == "stopped":
            sys.stdout.write(json.dumps({"text": "", "class": "stopped", "tooltip": ""}) + "\n")
            sys.stdout.flush()
            return
            
        display_text = self.scroll_text
        if len(display_text) > SCROLL_LIMIT:
            padded = display_text + "   •   "
            idx = self.scroll_idx % len(padded)
            display_text = (padded + padded)[idx:idx+SCROLL_LIMIT]
            
        player_name = self.active_player.props.player_name.lower()
        
        out = {
            "text": display_text,
            "alt": player_name,
            "class": self.current_class,
            "tooltip": self.scroll_text
        }
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
        
    def tick(self):
        if self.is_playing and len(self.scroll_text) > SCROLL_LIMIT:
            self.scroll_idx += 1
            self.output()
        return True

if __name__ == "__main__":
    s = Scroller()
    s.update_state()
    GLib.MainLoop().run()
