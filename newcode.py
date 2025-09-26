#!/usr/bin/python3
# -- coding: UTF-8 --

import serial
import pynmea2
import time
import sys

# ==========================
# CONFIGURATION
# ==========================
GPS_PORT = "/dev/ttyAMA0"      # NEO-6M GPS connected here
GPS_BAUDRATE = 9600

LORA_PORT = "/dev/ttyS0"       # LoRa HAT serial device (check with ls /dev/tty*)
LORA_BAUDRATE = 9600

SEND_INTERVAL = 2              # seconds between sends

# ==========================
# INIT GPS
# ==========================
try:
    gps_serial = serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=1)
    print("GPS initialized on", GPS_PORT)
except Exception as e:
    print("Error opening GPS serial:", e)
    sys.exit(1)

# ==========================
# INIT LORA
# ==========================
try:
    lora_serial = serial.Serial(LORA_PORT, LORA_BAUDRATE, timeout=1)
    print("LoRa initialized on", LORA_PORT)
except Exception as e:
    print("Error opening LoRa serial:", e)
    sys.exit(1)

# ==========================
# MAIN LOOP
# ==========================
def get_gps_coordinates():
    """Read from NEO-6M and return (lat, lon) or None"""
    try:
        line = gps_serial.readline().decode("ascii", errors="replace")
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            msg = pynmea2.parse(line)
            if msg.latitude and msg.longitude:
                return (msg.latitude, msg.longitude)
    except Exception:
        pass
    return None

print("Starting GPS → LoRa sender...")
while True:
    coords = get_gps_coordinates()
    if coords:
        lat, lon = coords
        payload = "{:.6f},{:.6f}".format(lat, lon)
        print("Sending:", payload)
        try:
            lora_serial.write((payload + "\n").encode())
        except Exception as e:
            print("LoRa send failed:", e)
        time.sleep(SEND_INTERVAL)
    else:
        print("No valid GPS fix...")
