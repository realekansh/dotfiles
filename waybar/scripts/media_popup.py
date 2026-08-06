#!/usr/bin/env python3
import sys
import os
import signal
import threading
import urllib.request
from urllib.parse import unquote

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('Playerctl', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GtkLayerShell, Playerctl

def cleanup(*args):
    Gtk.main_quit()
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def format_time(seconds):
    if seconds < 0:
        return "0:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"

class MediaPopup(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Media Popup")
        
        # Transparent window for glassmorphism
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 10)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 150)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.manager = Playerctl.PlayerManager()
        self.active_player = None
        self.manager.connect("name-appeared", self.on_player_appeared)
        self.manager.connect("player-vanished", self.on_player_vanished)

        self.current_cover_url = None
        self.dragging = False

        self.build_ui()
        self.apply_css()

        for name in self.manager.props.player_names:
            self.on_player_appeared(self.manager, name)

        GLib.timeout_add(100, self.update_position)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            cleanup()
            return True
        return False

    def on_focus_out(self, widget, event):
        import subprocess
        try:
            # Prevent closing if a screenshot/region selector is currently stealing focus
            for proc in ["slurp", "grim"]:
                if subprocess.run(["pgrep", "-x", proc], stdout=subprocess.DEVNULL).returncode == 0:
                    return False
            if subprocess.run(["pgrep", "-f", "hyprshot"], stdout=subprocess.DEVNULL).returncode == 0:
                return False
        except Exception:
            pass
        
        cleanup()
        return False

    def build_ui(self):
        # Reduced padding and spacing for compact, premium feel
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.set_name("main-container")
        self.add(self.main_box)

        # Album Art
        self.cover_box = Gtk.Box()
        self.cover_box.set_size_request(150, 150)
        self.cover_box.set_name("cover")
        self.cover_box.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(self.cover_box, False, False, 2)

        # Title & Artist Container
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(text_box, False, False, 0)

        # Song Title (Bold, wraps)
        self.lbl_title = Gtk.Label(xalign=0.5)
        self.lbl_title.set_name("title")
        self.lbl_title.set_line_wrap(True)
        self.lbl_title.set_lines(2)
        self.lbl_title.set_max_width_chars(30)
        self.lbl_title.set_justify(Gtk.Justification.CENTER)
        text_box.pack_start(self.lbl_title, False, False, 0)

        # Song Artist (Smaller, low opacity)
        self.lbl_artist = Gtk.Label(xalign=0.5)
        self.lbl_artist.set_name("artist")
        self.lbl_artist.set_ellipsize(3) # END
        self.lbl_artist.set_max_width_chars(35)
        text_box.pack_start(self.lbl_artist, False, False, 0)

        # Progress
        prog_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.main_box.pack_start(prog_box, False, False, 2)

        self.lbl_pos = Gtk.Label(label="0:00")
        self.lbl_pos.set_name("time-label")
        prog_box.pack_start(self.lbl_pos, False, False, 0)

        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider.set_draw_value(False)
        self.slider.connect("button-press-event", self.on_slider_press)
        self.slider.connect("button-release-event", self.on_slider_release)
        self.slider.connect("change-value", self.on_slider_changed)
        prog_box.pack_start(self.slider, True, True, 0)

        self.lbl_len = Gtk.Label(label="0:00")
        self.lbl_len.set_name("time-label")
        prog_box.pack_start(self.lbl_len, False, False, 0)

        # Controls
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_box.set_halign(Gtk.Align.CENTER)
        self.main_box.pack_start(ctrl_box, False, False, 2)

        self.btn_shuffle = Gtk.Button()
        self.img_shuffle = Gtk.Image.new_from_icon_name("media-playlist-shuffle-symbolic", Gtk.IconSize.BUTTON)
        self.btn_shuffle.set_image(self.img_shuffle)
        self.btn_shuffle.connect("clicked", self.on_shuffle)
        self.btn_shuffle.set_name("ctrl-btn-small")
        ctrl_box.pack_start(self.btn_shuffle, False, False, 0)

        # Previous (Smaller)
        self.btn_prev = Gtk.Button()
        self.btn_prev.set_image(Gtk.Image.new_from_icon_name("media-skip-backward-symbolic", Gtk.IconSize.BUTTON))
        self.btn_prev.connect("clicked", self.on_prev)
        self.btn_prev.set_name("ctrl-btn")
        ctrl_box.pack_start(self.btn_prev, False, False, 0)

        # Play/Pause (Primary, larger)
        self.btn_play = Gtk.Button()
        self.img_play = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.btn_play.set_image(self.img_play)
        self.btn_play.connect("clicked", self.on_play_pause)
        self.btn_play.set_name("ctrl-btn-play")
        ctrl_box.pack_start(self.btn_play, False, False, 0)

        # Next (Smaller)
        self.btn_next = Gtk.Button()
        self.btn_next.set_image(Gtk.Image.new_from_icon_name("media-skip-forward-symbolic", Gtk.IconSize.BUTTON))
        self.btn_next.connect("clicked", self.on_next)
        self.btn_next.set_name("ctrl-btn")
        ctrl_box.pack_start(self.btn_next, False, False, 0)
        
        self.btn_repeat = Gtk.Button()
        self.img_repeat = Gtk.Image.new_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
        self.btn_repeat.set_image(self.img_repeat)
        self.btn_repeat.connect("clicked", self.on_repeat)
        self.btn_repeat.set_name("ctrl-btn-small")
        ctrl_box.pack_start(self.btn_repeat, False, False, 0)


    def apply_css(self):
        css = b"""
        #main-container {
            background-color: rgba(30, 30, 46, 0.85); /* Glassmorphism surface */
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 20px;
            min-width: 310px;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.4);
        }
        #cover {
            border-radius: 16px;
            background-color: #313244;
            box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.4);
            transition: background-image 0.3s ease-in-out;
        }
        #title {
            color: #cdd6f4;
            font-weight: 800;
            font-size: 15px;
            font-family: 'Inter', sans-serif;
        }
        #artist {
            color: rgba(205, 214, 244, 0.6); /* Lower opacity */
            font-weight: 500;
            font-size: 13px;
            font-family: 'Inter', sans-serif;
            margin-top: 2px;
        }
        #time-label {
            color: #a6adc8;
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
        }
        scale trough {
            background-color: rgba(255, 255, 255, 0.1);
            min-height: 6px;
            border-radius: 6px;
        }
        scale highlight {
            background-color: #89b4fa;
            border-radius: 6px;
        }
        scale slider {
            background-color: #ffffff;
            min-width: 14px;
            min-height: 14px;
            border-radius: 50%;
            margin: -4px 0;
            box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 0, 0, 0.1);
            transition: all 0.15s cubic-bezier(0.4, 0.0, 0.2, 1);
        }
        scale slider:hover {
            background-color: #89b4fa; /* Accent color on hover */
            min-width: 16px;
            min-height: 16px;
            margin: -5px 0;
        }
        /* Prev/Next buttons (smaller) */
        button#ctrl-btn {
            background-color: transparent;
            color: #cdd6f4;
            border: none;
            border-radius: 20px;
            min-width: 36px;
            min-height: 36px;
            transition: all 0.15s ease;
        }
        /* Play button (Primary) */
        button#ctrl-btn-play {
            background-color: #89b4fa; /* Accent fill */
            color: #1e1e2e; /* Dark icon */
            border: none;
            border-radius: 26px;
            min-width: 52px;
            min-height: 52px;
            box-shadow: 0px 4px 10px rgba(137, 180, 250, 0.3);
            transition: all 0.15s ease;
        }
        button#ctrl-btn:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        button#ctrl-btn-play:hover {
            background-color: #b4befe;
            box-shadow: 0px 6px 14px rgba(137, 180, 250, 0.4);
        }
        button#ctrl-btn:active, button#ctrl-btn-play:active {
            opacity: 0.7;
        }
        /* Shuffle/Repeat buttons */
        button#ctrl-btn-small, button#ctrl-btn-small-active {
            background-color: transparent;
            color: rgba(205, 214, 244, 0.4); /* Neutral, low opacity */
            border: none;
            border-radius: 18px;
            min-width: 36px;
            min-height: 36px;
            transition: all 0.15s ease;
        }
        button#ctrl-btn-small-active {
            color: #89b4fa; /* Active accent */
            background-color: rgba(137, 180, 250, 0.1);
        }
        button#ctrl-btn-small:hover {
            color: rgba(205, 214, 244, 0.8);
            background-color: rgba(255, 255, 255, 0.05);
        }
        button#ctrl-btn-small-active:hover {
            background-color: rgba(137, 180, 250, 0.2);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_player_appeared(self, manager, name):
        player = Playerctl.Player.new_from_name(name)
        player.connect("metadata", self.on_metadata, manager)
        player.connect("playback-status", self.on_status, manager)
        manager.manage_player(player)
        self.update_active_player()

    def on_player_vanished(self, manager, player):
        self.update_active_player()

    def update_active_player(self):
        players = self.manager.props.players
        if not players:
            self.active_player = None
            self.lbl_title.set_text("No media playing")
            self.lbl_artist.set_text("")
            self.set_image(None)
            self.current_cover_url = None
            return

        playing = [p for p in players if p.props.playback_status == Playerctl.PlaybackStatus.PLAYING]
        paused = [p for p in players if p.props.playback_status == Playerctl.PlaybackStatus.PAUSED]
        
        if playing:
            self.active_player = playing[0]
        elif paused:
            self.active_player = paused[0]
        else:
            self.active_player = players[0]
            
        self.update_ui()

    def on_metadata(self, player, metadata, manager):
        if player == self.active_player:
            self.update_ui()
        else:
            self.update_active_player()

    def on_status(self, player, status, manager):
        self.update_active_player()

    def update_ui(self):
        if not self.active_player:
            return

        title = self.active_player.get_title() or "Unknown Title"
        artist = self.active_player.get_artist() or "Unknown Artist"
        
        self.lbl_title.set_text(title)
        self.lbl_artist.set_text(artist)

        self.update_play_button()

        # Update cover async
        try:
            art_url = self.active_player.print_metadata_prop("mpris:artUrl")
        except:
            art_url = None
            
        if art_url != self.current_cover_url:
            self.current_cover_url = art_url
            if art_url:
                threading.Thread(target=self.load_image, args=(art_url,), daemon=True).start()
            else:
                self.set_image(None)

    def load_image(self, url):
        try:
            if url.startswith("file://"):
                path = unquote(url[7:])
            else:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req).read()
                path = "/tmp/waybar_media_cover.jpg"
                with open(path, "wb") as f:
                    f.write(data)
            
            GLib.idle_add(self.set_image, path)
        except Exception as e:
            GLib.idle_add(self.set_image, None)

    def set_image(self, path):
        if path:
            css = f"#cover {{ background-image: url('file://{path}'); background-size: cover; background-position: center; }}"
        else:
            css = "#cover { background-image: none; background-color: #313244; }"
        
        if hasattr(self, 'cover_provider'):
            Gtk.StyleContext.remove_provider_for_screen(self.get_screen(), self.cover_provider)
        
        self.cover_provider = Gtk.CssProvider()
        self.cover_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), self.cover_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def update_play_button(self):
        if not self.active_player: return
        status = self.active_player.props.playback_status
        if status == Playerctl.PlaybackStatus.PLAYING:
            self.img_play.set_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.img_play.set_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)

        # Update shuffle button
        try:
            shuffle = self.active_player.props.shuffle
            self.btn_shuffle.set_name("ctrl-btn-small-active" if shuffle else "ctrl-btn-small")
        except:
            self.btn_shuffle.set_name("ctrl-btn-small")

        # Update repeat button
        try:
            loop = self.active_player.props.loop_status
            if loop == Playerctl.LoopStatus.TRACK:
                self.img_repeat.set_from_icon_name("media-playlist-repeat-song-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small-active")
            elif loop == Playerctl.LoopStatus.PLAYLIST:
                self.img_repeat.set_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small-active")
            else:
                self.img_repeat.set_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small")
        except:
            self.img_repeat.set_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
            self.btn_repeat.set_name("ctrl-btn-small")

    def update_position(self):
        if self.active_player and not self.dragging:
            try:
                pos = self.active_player.get_position() / 1000000.0
                length = self.active_player.print_metadata_prop("mpris:length")
                length = float(length) / 1000000.0 if length else 0

                if length > 0:
                    self.slider.set_range(0, length)
                    self.slider.set_value(pos)
                    self.lbl_len.set_text(format_time(length))
                self.lbl_pos.set_text(format_time(pos))
            except:
                pass
        return True

    def on_slider_press(self, widget, event):
        self.dragging = True
        return False

    def on_slider_release(self, widget, event):
        self.dragging = False
        if self.active_player:
            val = self.slider.get_value()
            self.active_player.set_position(int(val * 1000000))
        return False

    def on_slider_changed(self, scale, scroll, val):
        if self.active_player:
            self.lbl_pos.set_text(format_time(val))
        return False

    def on_shuffle(self, *args):
        if not self.active_player: return
        try:
            current = self.active_player.props.shuffle
            new_state = not current
            self.active_player.set_shuffle(new_state)
            self.btn_shuffle.set_name("ctrl-btn-small-active" if new_state else "ctrl-btn-small")
        except Exception:
            pass

    def on_repeat(self, *args):
        if not self.active_player: return
        try:
            current = self.active_player.props.loop_status
            if current == Playerctl.LoopStatus.NONE:
                self.active_player.set_loop_status(Playerctl.LoopStatus.PLAYLIST)
                self.img_repeat.set_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small-active")
            elif current == Playerctl.LoopStatus.PLAYLIST:
                self.active_player.set_loop_status(Playerctl.LoopStatus.TRACK)
                self.img_repeat.set_from_icon_name("media-playlist-repeat-song-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small-active")
            else:
                self.active_player.set_loop_status(Playerctl.LoopStatus.NONE)
                self.img_repeat.set_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
                self.btn_repeat.set_name("ctrl-btn-small")
        except Exception:
            pass

    def on_prev(self, *args):
        if self.active_player: self.active_player.previous()

    def on_next(self, *args):
        if self.active_player: self.active_player.next()

    def on_play_pause(self, *args):
        if self.active_player: self.active_player.play_pause()

win = MediaPopup()
win.show_all()
win.present()
Gtk.main()
