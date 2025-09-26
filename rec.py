#!/usr/bin/python3
# -- coding: UTF-8 --

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from tkintermapview import TkinterMapView
import serial
import serial.tools.list_ports
import re
import sys
import traceback
from datetime import datetime


class GPSReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚗 LoRa GPS Tracker")
        self.root.geometry("1280x780")
        self.root.configure(bg="#121212")

        # Serial variables
        self.serial_conn = None
        self.running = False

        # Path tracking
        self.path_points = []
        self.path_line = None
        self.auto_center = True

        # ---------------- Header ----------------
        header = tk.Frame(root, bg="#1f2937", height=50)
        header.pack(fill=tk.X)
        tk.Label(header, text="🚀 LoRa GPS Live Tracker",
                 fg="white", bg="#1f2937",
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=15, pady=10)

        # ---------------- Control Panel ----------------
        control_frame = tk.Frame(root, bg="#1e1e2e", height=60)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(control_frame, text="COM Port:", fg="white", bg="#1e1e2e", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(control_frame, textvariable=self.port_var,
                                      values=self.get_serial_ports(), width=10, state="readonly")
        self.port_menu.pack(side=tk.LEFT, padx=5)

        self.refresh_ports_button = tk.Button(control_frame, text="🔄 Refresh Ports", command=self.refresh_ports,
                                              bg="#2563eb", fg="white", relief="flat", padx=10, pady=5)
        self.refresh_ports_button.pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Baud Rate:", fg="white", bg="#1e1e2e", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.baud_var = tk.StringVar(value="9600")
        self.baud_entry = tk.Entry(control_frame, textvariable=self.baud_var, width=8,
                                   bg="#1f2937", fg="white", insertbackground="white", relief="flat")
        self.baud_entry.pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(control_frame, text="▶ Start", command=self.start_receiving,
                                      bg="#16a34a", fg="white", relief="flat", padx=12, pady=5)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(control_frame, text="⏹ Stop", command=self.stop_receiving,
                                     bg="#dc2626", fg="white", relief="flat", padx=12, pady=5)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.center_button = tk.Button(control_frame, text="📍 Auto-Center ON", command=self.toggle_center,
                                       bg="#0ea5e9", fg="white", relief="flat", padx=12, pady=5)
        self.center_button.pack(side=tk.RIGHT, padx=5)

        self.map_toggle_button = tk.Button(control_frame, text="🗺 Switch to Satellite", command=self.toggle_map,
                                           bg="#9333ea", fg="white", relief="flat", padx=12, pady=5)
        self.map_toggle_button.pack(side=tk.RIGHT, padx=5)

        # ---------------- Speed Display ----------------
        self.speed_var = tk.StringVar(value="Speed: 0.00 km/h")
        self.speed_label = tk.Label(root, textvariable=self.speed_var,
                                    font=("Segoe UI", 14, "bold"), fg="#22d3ee", bg="#121212")
        self.speed_label.pack(pady=5)

        # ---------------- Serial Output Panel ----------------
        output_frame = tk.LabelFrame(root, text="📜 Serial Output", fg="white", bg="#1e1e2e",
                                     font=("Segoe UI", 11, "bold"))
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_area = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10,
                                                   bg="#1f2937", fg="white", insertbackground="white",
                                                   relief="flat", font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.tag_config("success", foreground="lightgreen")
        self.text_area.tag_config("error", foreground="red")
        self.text_area.tag_config("info", foreground="cyan")

        # ---------------- Map Panel ----------------
        map_frame = tk.LabelFrame(root, text="🗺 Live Map", fg="white", bg="#1e1e2e", font=("Segoe UI", 11, "bold"))
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.map_widget = TkinterMapView(map_frame, width=1180, height=450, corner_radius=0)
        self.map_widget.set_position(20.5937, 78.9629)
        self.map_widget.set_zoom(5)
        self.set_street_map()
        self.map_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.marker = None
        self.path_line = None
        self.map_modes = ["street", "satellite", "hybrid"]
        self.map_mode_index = 0

        # ---------------- Status Bar ----------------
        self.status_var = tk.StringVar(value="🔌 Disconnected")
        status_bar = tk.Label(root, textvariable=self.status_var, anchor="w",
                              fg="white", bg="#1f2937", font=("Segoe UI", 9))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # ---------------- Window Close ----------------
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- Helper Functions ----------------
    def get_serial_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        self.port_menu["values"] = self.get_serial_ports()
        self.log_message("🔄 Ports refreshed", "info")
        # Reset map and path
        self.path_points.clear()
        if self.path_line:
            self.map_widget.delete(self.path_line)
            self.path_line = None
        if self.marker:
            self.map_widget.delete(self.marker)
            self.marker = None
        self.log_message("🗺 Map reset for new path", "info")

    def log_message(self, message, tag="normal"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.text_area.see(tk.END)
        self.text_area.configure(state="disabled")

    # ---------------- Serial Functions ----------------
    def start_receiving(self):
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Warning", "Please select a COM port")
            return
        baud = int(self.baud_var.get())
        try:
            self.serial_conn = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.log_message(f"✅ Connected to {port} at {baud} baud", "success")
            self.status_var.set(f"🟢 Connected to {port}")
            self.root.after(50, self.receive_data_loop)  # Start loop
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            self.log_message(f"❌ Connection failed: {e}", "error")

    def stop_receiving(self):
        self.running = False
        if self.serial_conn:
            try:
                if self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None
        self.log_message("⛔ Connection stopped", "error")
        self.status_var.set("🔌 Disconnected")

    def receive_data_loop(self):
        if not self.running or not self.serial_conn:
            return
        pattern = re.compile(r"LAT:([\d\.\-]+)\s+LON:([\d\.\-]+)\s+SPD:([\d\.]+)km/h")
        try:
            if self.serial_conn.in_waiting:
                line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    self.log_message(line)
                    match = pattern.search(line)
                    if match:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        spd = float(match.group(3))
                        self.update_map(lat, lon, spd)
        except serial.SerialException:
            self.log_message("⚠️ Serial port disconnected!", "error")
            self.stop_receiving()
        except Exception as e:
            self.log_message(f"⚠️ Error reading data: {e}", "error")
        finally:
            self.root.after(50, self.receive_data_loop)  # Schedule next check

    # ---------------- Map Functions ----------------
    def update_map(self, lat, lon, spd):
        self.speed_var.set(f"Speed: {spd:.2f} km/h")
        marker_color = "green" if spd > 0 else "red"

        if self.marker:
            self.marker.set_position(lat, lon)
            self.marker.set_text(f"📍 LoRa GPS\nSpeed: {spd:.2f} km/h")
        else:
            self.marker = self.map_widget.set_marker(lat, lon,
                                                     text=f"📍 LoRa GPS\nSpeed: {spd:.2f} km/h",
                                                     marker_color_circle=marker_color)

        self.path_points.append((lat, lon))
        if len(self.path_points) > 1:
            if self.path_line:
                self.map_widget.delete(self.path_line)
            self.path_line = self.map_widget.set_path(self.path_points, color="cyan", width=3)

        if self.auto_center:
            self.map_widget.set_position(lat, lon)

    def set_street_map(self):
        self.map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", max_zoom=20)

    def set_satellite_map(self):
        self.map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", max_zoom=20)

    def set_hybrid_map(self):
        self.map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", max_zoom=20)

    def toggle_map(self):
        self.map_mode_index = (self.map_mode_index + 1) % len(self.map_modes)
        mode = self.map_modes[self.map_mode_index]
        if mode == "street":
            self.set_street_map()
            self.map_toggle_button.config(text="🗺 Switch to Satellite")
        elif mode == "satellite":
            self.set_satellite_map()
            self.map_toggle_button.config(text="🗺 Switch to Hybrid")
        elif mode == "hybrid":
            self.set_hybrid_map()
            self.map_toggle_button.config(text="🗺 Switch to Street")

    def toggle_center(self):
        self.auto_center = not self.auto_center
        status = "ON" if self.auto_center else "OFF"
        self.center_button.config(text=f"📍 Auto-Center {status}")

    # ---------------- Close ----------------
    def on_close(self):
        self.stop_receiving()
        self.root.destroy()


# ---------------- Global Exception Handler ----------------
def global_exception_handler(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        if "app" in globals() and hasattr(app, "log_message"):
            app.log_message(f"⚠️ Unhandled Error: {exc_value}", "error")
        else:
            print("⚠️ Unhandled Exception:", error_msg)
    except Exception:
        print("⚠️ Unhandled Exception:", error_msg)


if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    root = tk.Tk()
    app = GPSReceiverApp(root)
    root.mainloop()
