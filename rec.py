#!/usr/bin/python3
# -- coding: UTF-8 --
import serial
import time
from datetime import datetime
import sys
import os
import math

# ===============================
# CONFIGURATION
# ===============================
UART_PORT = "/dev/ttyAMA0"  # GPS UART port (example)
BAUDRATE = 9600             # GPS baud rate
SEND_INTERVAL = 1.0         # Send interval in seconds

# ===============================
# Initialize UART
# ===============================
def init_serial():
    if not os.path.exists(UART_PORT):
        print(f"[FATAL] {UART_PORT} not found! Check wiring and enable UART in raspi-config.")
        sys.exit(1)
    try:
        ser = serial.Serial(UART_PORT, BAUDRATE, timeout=1)
        print(f"[INFO] UART connected on port {UART_PORT}")
        return ser
    except serial.SerialException as e:
        print(f"[ERROR] Unable to open UART: {e}")
        sys.exit(1)

# ===============================
# Parse GPRMC NMEA sentence
# ===============================
def parse_gprmc(sentence):
    try:
        parts = sentence.split(",")
        if len(parts) < 9:
            return None

        if parts[2] != "A":  # "A" means valid fix
            return None

        # Latitude
        raw_lat = parts[3]
        lat_dir = parts[4]
        lat_deg = float(raw_lat[:2])
        lat_min = float(raw_lat[2:])
        lat = lat_deg + (lat_min / 60.0)
        if lat_dir == "S":
            lat = -lat

        # Longitude
        raw_lon = parts[5]
        lon_dir = parts[6]
        lon_deg = float(raw_lon[:3])
        lon_min = float(raw_lon[3:])
        lon = lon_deg + (lon_min / 60.0)
        if lon_dir == "W":
            lon = -lon

        # Speed (knots → km/h)
        spd_knots = float(parts[7]) if parts[7] else 0.0
        speed_kmh = spd_knots * 1.852

        return lat, lon, speed_kmh
    except Exception:
        return None

# ===============================
# Main Loop
# ===============================
def main():
    ser = init_serial()
    print("======================================")
    print("  GPS + Speed Calculation + LoRa Sender (No pynmea2)")
    print("======================================")

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith("$GPRMC"):
                continue

            parsed = parse_gprmc(line)
            if parsed:
                lat, lon, speed_kmh = parsed
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                message = f"{timestamp} LAT:{lat:.7f} LON:{lon:.7f} SPEED:{speed_kmh:.2f}km/h"

                # TODO: Replace this with your LoRa transmit function
                # Example: lora.send(message.encode())
                print(f"[LORA] {message}")

                time.sleep(SEND_INTERVAL)

        except KeyboardInterrupt:
            print("\n[INFO] Exiting gracefully...")
            ser.close()
            sys.exit(0)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
