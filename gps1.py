#!/usr/bin/python3
# -- coding: UTF-8 --

import serial
import pynmea2
import time
from datetime import datetime, timezone
import sys, os, math
from LoRaRF import SX126x   # LoRa driver

# ===============================
# CONFIGURATION
# ===============================
UART_PORT = "/dev/ttyAMA0"   # GPS UART port
GPS_BAUD = 9600
SEND_INTERVAL = 1.0          # Seconds

LORA_FREQ = 868000000        # 868 MHz
LORA_BW = 125000             # Bandwidth: 125 kHz
LORA_SF = 9                  # Spreading Factor: 9 (balance)
LORA_CR = 5                  # Coding Rate 4/5
LORA_POWER = 22              # TX Power (dBm)

# ===============================
# Haversine distance (for speed)
# ===============================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 1000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))  # meters

# ===============================
# Setup GPS
# ===============================
def init_gps():
    if not os.path.exists(UART_PORT):
        print(f"[FATAL] {UART_PORT} not found! Enable UART in raspi-config.")
        sys.exit(1)
    try:
        gps = serial.Serial(UART_PORT, GPS_BAUD, timeout=1)
        print("[INFO] GPS UART connected")
        return gps
    except Exception as e:
        print(f"[ERROR] GPS UART error: {e}")
        sys.exit(1)

# ===============================
# Setup LoRa
# ===============================
def init_lora():
    lora = SX126x()
    lora.begin(freq=LORA_FREQ, bw=LORA_BW, sf=LORA_SF, cr=LORA_CR, syncWord=0x12, power=LORA_POWER)
    print("[INFO] LoRa initialized @ 868MHz")
    return lora

# ===============================
# Main Loop
# ===============================
def main():
    gps = init_gps()
    lora = init_lora()

    last_lat, last_lon, last_time = None, None, None

    while True:
        try:
            line = gps.readline().decode('ascii', errors='ignore').strip()
            if not line:
                continue

            if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                try:
                    msg = pynmea2.parse(line)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude') and msg.latitude and msg.longitude:
                        lat, lon = float(msg.latitude), float(msg.longitude)

                        gps_time = None
                        if hasattr(msg, 'timestamp') and msg.timestamp:
                            now_utc = datetime.utcnow()
                            gps_time = datetime.combine(now_utc.date(), msg.timestamp, tzinfo=timezone.utc).timestamp()
                        current_time = gps_time if gps_time else time.time()

                        speed_kmh = 0.0
                        if last_lat and last_lon and last_time:
                            dist_m = haversine(last_lat, last_lon, lat, lon)
                            delta_t = current_time - last_time
                            if delta_t > 0 and dist_m > 0.5:
                                speed_kmh = (dist_m / delta_t) * 3.6  # m/s → km/h

                        last_lat, last_lon, last_time = lat, lon, current_time

                        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        message = f"{timestamp} LAT:{lat:.6f} LON:{lon:.6f} SPD:{speed_kmh:.2f}km/h"

                        lora.send(message.encode())
                        print(f"[LORA TX] {message}")

                        time.sleep(SEND_INTERVAL)

                except pynmea2.ParseError:
                    continue

        except KeyboardInterrupt:
            print("\n[INFO] Exiting...")
            gps.close()
            sys.exit(0)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
