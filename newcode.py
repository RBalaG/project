#!/usr/bin/python3
# -- coding: UTF-8 --

import serial
import pynmea2
import time
import sys

# ==========================
# CONFIGURATION
# ==========================
GPS_PORT = "/dev/ttyUSB0"      # GPS via USB-to-UART adapter
GPS_BAUDRATE = 9600

LORA_PORT = "/dev/serial0"     # LoRa HAT on GPIO UART
LORA_BAUDRATE = 9600

SEND_INTERVAL = 2              # seconds between transmissions

# ==========================
# INIT SERIAL PORTS
# ==========================
def init_serial(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"[ OK ] Opened {port} at {baud} baud")
        return ser
    except Exception as e:
        print(f"[ERR] Could not open {port}: {e}")
        sys.exit(1)

gps_serial = init_serial(GPS_PORT, GPS_BAUDRATE)
lora_serial = init_serial(LORA_PORT, LORA_BAUDRATE)

# ==========================
# READ GPS FUNCTION
# ==========================
def get_gps_coordinates():
    """Read from NEO-6M and return (lat, lon) or None"""
    try:
        line = gps_serial.readline().decode("ascii", errors="replace").strip()
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            msg = pynmea2.parse(line)
            if msg.latitude and msg.longitude:
                return (msg.latitude, msg.longitude)
    except Exception:
        pass
    return None

# ==========================
# MAIN LOOP
# ==========================
print("🚀 Starting GPS → LoRa sender...")
while True:
    coords = get_gps_coordinates()
    if coords:
        lat, lon = coords
        payload = f"{lat:.6f},{lon:.6f}"
        try:
            lora_serial.write((payload + "\n").encode())
            print(f"[SENT] {payload}")
        except Exception as e:
            print(f"[ERR] LoRa send failed: {e}")
    else:
        print("[..] Waiting for GPS fix...")
    time.sleep(SEND_INTERVAL)
