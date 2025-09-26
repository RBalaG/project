#!/usr/bin/python3
# -- coding: UTF-8 --

import serial
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from tkintermapview import TkinterMapView
from datetime import datetime
import sys
import os
import re
from typing import Optional, Tuple

# ===============================
# CONFIGURATION
# ===============================
UART_PORT = "COM9"   # Change for your setup
BAUDRATE = 9600


# ===============================
# LoRa Receiver Class
# ===============================
class LoRaReceiver:
    def __init__(self, port: str, baudrate: int = 9600):
        if not self.is_port_valid(port):
            print(f"[FATAL] Serial port '{port}' not found or invalid.")
            sys.exit(1)
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.ser.reset_input_buffer()
        except serial.SerialException as e:
            print(f"[ERROR] Unable to open serial port '{port}': {e}")
            sys.exit(1)

    @staticmethod
    def is_port_valid(port: str) -> bool:
        """Validate serial port name."""
        if os.name == "nt":  # Windows: allow COMxx
            return bool(re.match(r"COM[0-9]+", port.upper()))
        else:  # Linux: check device path
            return os.path.exists(port)

    def receive(self) -> Optional[str]:
        """Read one line if available."""
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode(errors="ignore").strip()
                return data
        except serial.SerialException as e:
            print(f"[ERROR] Serial read error: {e}")
        return None

    def close(self) -> None:
        try:
            self.ser.close()
        except serial.SerialException:
            pass


# ===============================
# Parse GPS + Speed message
# ===============================
def parse_lora_message(msg: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Extract latitude, longitude, speed from LoRa message.
    Accepts both SPD: and SPEED: formats.
    """
    pattern = r"LAT:([\-0-9.]+)\s+LON:([\-0-9.]+)\s+(?:SPD|SPEED):([0-9.]+)km/h"
    match = re.search(pattern, msg)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            speed = float(match.group(3))
            return lat, lon, speed
        except ValueError:
            return None, None, None
    return None, None, None


# ===============================
# GUI Application
# ===============================
class GPSReceiverApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LoRa GPS Receiver")
        self.root.geometry("1200x780")
        self.root.configure(bg="#1e1e2f")

        # Fonts
        self.title_font = ("Helvetica", 14, "bold")
        self.info_font = ("Helvetica", 12, "bold")
        self.msg_font = ("Courier", 11)

        # === Top info frame ===
        top_frame = tk.Frame(root, bg="#2e2e3f", height=70)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

        # Clock box
        clock_frame = tk.Frame(top_frame, bg="#3e3e5f", bd=2, relief=tk.RIDGE)
        clock_frame.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(clock_frame, text="Clock", font=self.info_font, fg="#ffffff", bg="#3e3e5f").pack()
        self.clock_label = tk.Label(clock_frame, text="", font=self.title_font, fg="#00ffff", bg="#3e3e5f")
        self.clock_label.pack(padx=10, pady=5)

        # Speed box
        speed_frame = tk.Frame(top_frame, bg="#3e3e5f", bd=2, relief=tk.RIDGE)
        speed_frame.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(speed_frame, text="Speed", font=self.info_font, fg="#ffffff", bg="#3e3e5f").pack()
        self.speed_label = tk.Label(speed_frame, text="0.00 km/h", font=self.title_font, fg="#00ff00", bg="#3e3e5f")
        self.speed_label.pack(padx=10, pady=5)

        # Status box
        status_frame = tk.Frame(top_frame, bg="#3e3e5f", bd=2, relief=tk.RIDGE)
        status_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        tk.Label(status_frame, text="Status", font=self.info_font, fg="#ffffff", bg="#3e3e5f").pack(anchor="w", padx=5)
        self.status_label = tk.Label(status_frame, text="Waiting for LoRa data...", font=self.info_font, fg="#ffff00", bg="#3e3e5f")
        self.status_label.pack(anchor="w", padx=5, pady=5)

        # === Map panel ===
        map_frame = tk.Frame(root, bg="#1e1e2f")
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.map_widget = TkinterMapView(map_frame, width=1180, height=450, corner_radius=0)
        self.map_widget.set_position(20.5937, 78.9629)  # Default to India
        self.map_widget.set_zoom(5)
        self.map_widget.pack()
        self.marker = None

        # === Message log ===
        bottom_frame = tk.Frame(root, bg="#1e1e2f")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=5)
        tk.Label(bottom_frame, text="Received Messages:", font=self.info_font, fg="#ffffff", bg="#1e1e2f").pack(anchor="w", padx=5)
        self.message_box = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD, height=8, font=self.msg_font,
                                                     bg="#2e2e3f", fg="#ffffff", insertbackground="#ffffff")
        self.message_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.message_box.configure(state="disabled")

        # LoRa receiver
        self.receiver = LoRaReceiver(UART_PORT, BAUDRATE)
        self.running = True

        # Start background reader + clock
        threading.Thread(target=self.read_lora_data, daemon=True).start()
        self.update_clock()

    def read_lora_data(self) -> None:
        """Read LoRa data continuously in thread."""
        while self.running:
            msg = self.receiver.receive()
            if msg:
                self.log_message(msg)
                lat, lon, speed = parse_lora_message(msg)
                if lat is not None and lon is not None:
                    self.update_map(lat, lon)
                    self.update_speed(speed)
                    self.status_label.config(text=f"Fix: LAT={lat:.6f}, LON={lon:.6f}", fg="#00ff00")
                else:
                    self.status_label.config(text="Invalid data received", fg="#ff0000")
            time.sleep(0.1)

    def update_speed(self, speed_kmh: float) -> None:
        """Update speed label color-coded."""
        if speed_kmh < 5:
            color = "#00ff00"
        elif speed_kmh < 20:
            color = "#ffa500"
        else:
            color = "#ff0000"
        self.speed_label.config(text=f"{speed_kmh:.2f} km/h", fg=color)

    def update_map(self, lat: float, lon: float) -> None:
        """Update map + marker."""
        try:
            self.map_widget.set_position(lat, lon)
            self.map_widget.set_zoom(18)
            if self.marker:
                self.marker.set_position(lat, lon)
            else:
                self.marker = self.map_widget.set_marker(lat, lon, text="Current Location")
        except Exception as e:
            print(f"[WARN] Map update failed: {e}")

    def log_message(self, msg: str) -> None:
        """Append a message to log with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_box.configure(state="normal")
        self.message_box.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.message_box.yview(tk.END)
        self.message_box.configure(state="disabled")

    def update_clock(self) -> None:
        """Update clock label."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=current_time)
        self.root.after(1000, self.update_clock)

    def on_close(self) -> None:
        """Stop gracefully."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.running = False
            self.receiver.close()
            self.root.destroy()


# ===============================
# Main
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    app = GPSReceiverApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
