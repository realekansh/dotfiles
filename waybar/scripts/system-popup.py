#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell, GLib, Gdk
import os
import sys
import signal
import time
import subprocess
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

CONFIG_PATH = os.path.expanduser("~/.config/waybar/scripts/system-popup.toml")

def load_config():
    default_config = {
        "system": {
            "cpu": True, "ram": True, "gpu": True, "storage": True,
            "network_speed": True, "temperature": True,
            "updates": True, "github": False
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "rb") as f:
                user_config = tomllib.load(f)
                if "system" in user_config:
                    default_config["system"].update(user_config["system"])
        except Exception as e:
            print(f"Error parsing config: {e}")
    return default_config["system"]

class SystemPopup(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = load_config()
        
        # State
        self.is_visible = False
        self.update_timer = None
        self.fast_timer = None
        self.last_cpu_idle = 0
        self.last_cpu_total = 0
        self.last_net_rx = 0
        self.last_net_tx = 0
        self.last_net_time = 0

        # UI Setup
        self.set_title("System Popup")
        self.set_decorated(False)
        self.set_name("system-popup")
        
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "system-popup")
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 15)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 15)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("key-press-event", self.on_key_press)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.add(main_box)
        
        # --- 1. Connectivity ---
        conn_label = Gtk.Label(label="Connectivity")
        conn_label.set_halign(Gtk.Align.START)
        conn_label.get_style_context().add_class("section-title")
        main_box.pack_start(conn_label, False, False, 0)
        
        conn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        main_box.pack_start(conn_box, False, False, 0)
        
        self.wifi_btn = Gtk.ToggleButton(label="   Wi-Fi")
        self.eth_btn = Gtk.ToggleButton(label="󰈀   Ethernet")
        self.bt_btn = Gtk.ToggleButton(label="   Bluetooth")
        
        for btn in [self.wifi_btn, self.eth_btn, self.bt_btn]:
            btn.get_style_context().add_class("conn-btn")
            conn_box.pack_start(btn, True, True, 0)
            btn.connect("toggled", self.on_conn_toggled)
            
        # --- 2. System ---
        sys_label = Gtk.Label(label="System")
        sys_label.set_halign(Gtk.Align.START)
        sys_label.get_style_context().add_class("section-title")
        main_box.pack_start(sys_label, False, False, 0)
        
        self.sys_grid = Gtk.Grid(column_spacing=25, row_spacing=20)
        main_box.pack_start(self.sys_grid, False, False, 0)
        
        self.metrics = {}
        row, col = 0, 0
        
        def add_metric(key, icon, name):
            nonlocal col, row
            if not self.config.get(key, False): return
            
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            
            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.get_style_context().add_class("metric-icon")
            icon_lbl.set_valign(Gtk.Align.CENTER)
            
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            vbox.set_valign(Gtk.Align.CENTER)
            
            name_lbl = Gtk.Label(label=name)
            name_lbl.set_halign(Gtk.Align.START)
            name_lbl.get_style_context().add_class("metric-name")
            
            val_lbl = Gtk.Label(label="--")
            val_lbl.set_halign(Gtk.Align.START)
            val_lbl.get_style_context().add_class("metric-val")
            
            vbox.pack_start(name_lbl, False, False, 0)
            vbox.pack_start(val_lbl, False, False, 0)
            
            box.pack_start(icon_lbl, False, False, 0)
            box.pack_start(vbox, True, True, 0)
            
            # Make boxes equal width for clean grid layout
            box.set_size_request(140, -1)
            
            self.sys_grid.attach(box, col, row, 1, 1)
            self.metrics[key] = val_lbl
            
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        add_metric("cpu", "", "CPU Usage")
        add_metric("ram", "", "Memory")
        add_metric("gpu", "󰢮", "GPU Usage")
        add_metric("storage", "", "Storage")
        add_metric("temperature", "", "Temperature")
        add_metric("network_speed", "󰓢", "Network")
        add_metric("updates", "", "Updates")
        add_metric("github", "", "GitHub")
        
        self.load_css()
        
    def load_css(self):
        css = b"""
        window#system-popup {
            background-color: rgba(30, 30, 46, 0.90);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .section-title {
            font-weight: 800;
            font-size: 15px;
            color: #cdd6f4;
            margin-bottom: 5px;
        }
        .conn-btn {
            border-radius: 12px;
            padding: 10px 16px;
            background-color: rgba(255, 255, 255, 0.05);
            color: #a6adc8;
            font-weight: bold;
            font-size: 13px;
            border: 1px solid transparent;
            box-shadow: none;
            text-shadow: none;
        }
        .conn-btn:checked {
            background-color: #89b4fa;
            color: #1e1e2e;
        }
        .conn-btn:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .metric-icon {
            font-size: 22px;
            color: #89b4fa;
            min-width: 35px;
        }
        .metric-name {
            font-size: 12px;
            color: #a6adc8;
        }
        .metric-val {
            font-size: 15px;
            font-weight: 900;
            color: #cdd6f4;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
    def on_conn_toggled(self, btn):
        if not self.is_visible: return
        # A real implementation would run rfkill/nmcli here.
        # But we want minimal side-effects, so we leave it as an aesthetic toggle 
        # unless configured to actually alter system state.
        pass

    def check_connectivity(self):
        try:
            wifi = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True).stdout.strip()
            self.wifi_btn.set_active(wifi == "enabled")
        except: pass
        
        try:
            bt = subprocess.run(["rfkill", "list", "bluetooth"], capture_output=True, text=True).stdout
            self.bt_btn.set_active("Soft blocked: yes" not in bt and bt.strip() != "")
        except: pass
        
    def toggle(self):
        if self.is_visible:
            self.hide_popup()
        else:
            self.show_popup()
            
    def show_popup(self):
        self.is_visible = True
        self.show_all()
        self.present()
        self.check_connectivity()
        self.update_metrics_slow()
        self.update_metrics_fast()
        # High frequency for network speed
        self.fast_timer = GLib.timeout_add(1000, self.update_metrics_fast)
        # Low frequency for heavy metrics
        self.update_timer = GLib.timeout_add(3000, self.update_metrics_slow)
        
    def hide_popup(self):
        self.is_visible = False
        self.hide()
        if self.fast_timer:
            GLib.source_remove(self.fast_timer)
            self.fast_timer = None
        if self.update_timer:
            GLib.source_remove(self.update_timer)
            self.update_timer = None
            
    def on_focus_out(self, widget, event):
        self.hide_popup()
        return False
        
    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_popup()
            return True
        return False
        
    def update_metrics_fast(self):
        if "network_speed" in self.metrics:
            try:
                with open("/proc/net/dev", "r") as f:
                    lines = f.readlines()[2:]
                rx, tx = 0, 0
                for line in lines:
                    parts = line.split()
                    iface = parts[0].strip(":")
                    # Ignore loopback and virtual interfaces for realistic speed
                    if iface != "lo" and not iface.startswith(("veth", "docker", "br-")):
                        rx += int(parts[1])
                        tx += int(parts[9])
                
                now = time.time()
                if self.last_net_time > 0:
                    dt = now - self.last_net_time
                    rx_rate = (rx - self.last_net_rx) / dt
                    tx_rate = (tx - self.last_net_tx) / dt
                    
                    def fmt(b):
                        if b > 1048576: return f"{b/1048576:.1f} MB/s"
                        if b > 1024: return f"{b/1024:.0f} KB/s"
                        return f"{b:.0f} B/s"
                        
                    self.metrics["network_speed"].set_label(f"↓ {fmt(rx_rate)}   ↑ {fmt(tx_rate)}")
                    
                self.last_net_rx = rx
                self.last_net_tx = tx
                self.last_net_time = now
            except Exception:
                self.metrics["network_speed"].set_label("N/A")
        return True
        
    def update_metrics_slow(self):
        if "cpu" in self.metrics:
            try:
                with open("/proc/stat", "r") as f:
                    fields = [float(col) for col in f.readline().strip().split()[1:]]
                idle, total = fields[3], sum(fields)
                idle_delta = idle - self.last_cpu_idle
                total_delta = total - self.last_cpu_total
                self.last_cpu_idle, self.last_cpu_total = idle, total
                if total_delta > 0:
                    usage = 100.0 * (1.0 - idle_delta / total_delta)
                    self.metrics["cpu"].set_label(f"{usage:.1f}%")
            except Exception:
                pass
                
        if "ram" in self.metrics:
            try:
                with open("/proc/meminfo", "r") as f:
                    mem = {}
                    for line in f:
                        k, v = line.split()[0:2]
                        mem[k.strip(":")] = int(v)
                total = mem["MemTotal"]
                free = mem["MemFree"] + mem["Buffers"] + mem["Cached"] + mem.get("SReclaimable", 0)
                used = total - free
                self.metrics["ram"].set_label(f"{used/1048576:.1f} GB")
            except Exception:
                pass
                
        if "storage" in self.metrics:
            try:
                st = os.statvfs('/')
                total = st.f_blocks * st.f_frsize
                free = st.f_bavail * st.f_frsize
                used = total - free
                perc = (used / total) * 100
                self.metrics["storage"].set_label(f"{used/(1024**3):.0f} GB ({perc:.0f}%)")
            except Exception:
                pass
                
        if "temperature" in self.metrics:
            try:
                temps = []
                for zone in os.listdir("/sys/class/thermal/"):
                    if zone.startswith("thermal_zone"):
                        with open(f"/sys/class/thermal/{zone}/temp", "r") as f:
                            t = int(f.read().strip()) / 1000.0
                            if t > 0: temps.append(t)
                if temps:
                    self.metrics["temperature"].set_label(f"{max(temps):.0f}°C")
            except Exception:
                pass
                
        if "gpu" in self.metrics:
            try:
                if os.path.exists("/sys/class/drm/card0/device/gpu_busy_percent"):
                    with open("/sys/class/drm/card0/device/gpu_busy_percent", "r") as f:
                        gpu = f.read().strip()
                        self.metrics["gpu"].set_label(f"{gpu}%")
                else:
                    self.metrics["gpu"].set_label("N/A")
            except Exception:
                pass
                
        if "updates" in self.metrics:
            try:
                if os.path.exists("/tmp/updates.txt"):
                    with open("/tmp/updates.txt", "r") as f:
                        self.metrics["updates"].set_label(f.read().strip() + " pkgs")
                else:
                    self.metrics["updates"].set_label("Up to date")
            except: pass
            
        return True

def on_signal(sig, frame):
    if win:
        win.toggle()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "toggle":
        os.system("pkill -SIGUSR1 -f 'python3.*system-popup.py$'")
        sys.exit(0)
        
    win = SystemPopup()
    signal.signal(signal.SIGUSR1, on_signal)
    
    # Run loop
    GLib.MainLoop().run()
