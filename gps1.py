#!/usr/bin/python3
# -- coding: UTF-8 --
"""
GPS -> LoRa sender (improved):
- Uses SX126x driver (LoRaRF) when available (SPI)
- Falls back to AT-command mode on UART if driver missing
- Uses GPRMC speed over ground (SOG) for accurate speed
- Filters small GPS jitter to avoid wrong locations/speed
"""

import os
import sys
import time
import math
import serial
import pynmea2
from datetime import datetime, timezone

# Try to import SX126x driver (LoRaRF). If not available, we'll use AT mode.
try:
    from LoRaRF import SX126x
    HAS_SX126X = True
except Exception:
    SX126x = None
    HAS_SX126X = False

# ===============================
# CONFIGURATION
# ===============================
GPS_PORT = "/dev/ttyAMA0"    # GPS serial port
GPS_BAUD = 9600

LORA_AT_PORT = "/dev/serial0"  # AT-mode UART
LORA_AT_BAUD = 9600

LORA_FREQ = 868000000    # 868 MHz
LORA_BW = 125000
LORA_SF = 9
LORA_CR = 5
LORA_POWER = 22

SEND_INTERVAL = 1.0      # seconds between messages
GPS_JITTER_THRESHOLD = 1.0  # meters

# ===============================
# Utility: Haversine distance in meters
# ===============================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0  # earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# ===============================
# Init GPS serial
# ===============================
def init_gps():
    if not os.path.exists(GPS_PORT):
        print(f"[FATAL] GPS port '{GPS_PORT}' not found.")
        sys.exit(1)
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        time.sleep(0.5)
        ser.reset_input_buffer()
        print(f"[INFO] GPS connected on {GPS_PORT} @ {GPS_BAUD}")
        return ser
    except serial.SerialException as e:
        print(f"[FATAL] Could not open GPS serial: {e}")
        sys.exit(1)

# ===============================
# LoRa driver (SX126x)
# ===============================
def init_lora_driver():
    if not HAS_SX126X:
        return None
    try:
        lora = SX126x()
        lora.begin(
            freq=LORA_FREQ,
            bw=LORA_BW,
            sf=LORA_SF,
            cr=LORA_CR,
            syncWord=0x12,
            power=LORA_POWER,
            currentLimit=60.0
        )
        print(f"[INFO] SX126x init OK: {LORA_FREQ//1000000}MHz SF{LORA_SF}")
        return ('sx', lora)
    except Exception as e:
        print(f"[WARN] SX126x init failed: {e}")
        return None

# ===============================
# LoRa AT-mode initialization
# ===============================
def init_lora_at():
    if not os.path.exists(LORA_AT_PORT):
        print(f"[WARN] AT-mode port '{LORA_AT_PORT}' not found.")
        return None
    try:
        at = serial.Serial(LORA_AT_PORT, LORA_AT_BAUD, timeout=1)
        time.sleep(0.5)
        at.reset_input_buffer()
        print(f"[INFO] LoRa AT serial opened on {LORA_AT_PORT} @ {LORA_AT_BAUD}")
    except Exception as e:
        print(f"[WARN] Cannot open AT serial: {e}")
        return None

    def at_write(cmd, wait=0.1):
        try:
            at.write((cmd + "\r\n").encode())
            time.sleep(wait)
            return at.read_all().decode(errors='ignore').strip()
        except:
            return ""
    
    # Configure AT module (best effort)
    try:
        at_write("AT")
        at_write(f"AT+FREQ={LORA_FREQ}")
        at_write(f"AT+SF={LORA_SF}")
        at_write(f"AT+BW={int(LORA_BW/1000)}")
        at_write(f"AT+CR=4/{LORA_CR}")
        at_write(f"AT+POWER={LORA_POWER}")
        print("[INFO] AT-mode LoRa configured.")
    except Exception as e:
        print(f"[WARN] AT config may have failed: {e}")

    return ('at', at)

# ===============================
# Generic send wrapper
# ===============================
def send_lora(iface, handle, text):
    if iface == 'sx':
        lora = handle
        try:
            if hasattr(lora, "send"):
                lora.send(text)
                return True
            if hasattr(lora, "beginPacket"):
                lora.beginPacket()
                lora.print(text)
                lora.endPacket()
                return True
            if hasattr(lora, "write"):
                lora.write(text.encode())
                return True
        except Exception as e:
            print(f"[ERROR] SX126x send failed: {e}")
            return False
    elif iface == 'at':
        at = handle
        try:
            cmd = f"AT+SEND={text}"
            at.write((cmd + "\r\n").encode())
            time.sleep(0.1)
            resp = at.read_all().decode(errors='ignore').strip()
            return True
        except Exception as e:
            print(f"[ERROR] AT send failed: {e}")
            return False
    return False

# ===============================
# Main
# ===============================
def main():
    gps = init_gps()
    lora_iface = None
    lora_handle = None

    if HAS_SX126X:
        res = init_lora_driver()
        if res:
            lora_iface, lora_handle = res
    if lora_iface is None:
        res = init_lora_at()
        if res:
            lora_iface, lora_handle = res
    if lora_iface is None:
        print("[FATAL] No LoRa interface available.")
        sys.exit(1)

    print("=== GPS -> LoRa Sender (Updated) ===")

    last_lat = last_lon = None

    try:
        while True:
            line = gps.readline().decode('ascii', errors='ignore').strip()
            if not line:
                time.sleep(0.05)
                continue

            if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                try:
                    msg = pynmea2.parse(line)
                except pynmea2.ParseError:
                    continue

                if not (msg.latitude and msg.longitude):
                    continue

                lat = float(msg.latitude)
                lon = float(msg.longitude)

                # Use SOG (knots) from NMEA if available
                speed_kmh = 0.0
                if hasattr(msg, "spd_over_grnd") and msg.spd_over_grnd:
                    speed_kmh = float(msg.spd_over_grnd) * 1.852  # knots -> km/h

                # Filter GPS jitter
                if last_lat is not None and last_lon is not None:
                    dist = haversine_m(last_lat, last_lon, lat, lon)
                    if dist < GPS_JITTER_THRESHOLD:
                        # Ignore tiny movements
                        lat, lon = last_lat, last_lon
                        if speed_kmh < 0.5:
                            speed_kmh = 0.0

                last_lat, last_lon = lat, lon

                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                payload = f"{timestamp} LAT:{lat:.7f} LON:{lon:.7f} SPD:{speed_kmh:.2f}km/h"

                if send_lora(lora_iface, lora_handle, payload):
                    print(f"[TX] {payload}")
                else:
                    print(f"[TX-FAIL] {payload}")

                time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user, exiting...")
    finally:
        try: gps.close()
        except: pass
        if lora_iface == 'at' and lora_handle:
            try: lora_handle.close()
            except: pass
        print("[INFO] Clean exit.")

if __name__ == "__main__":
    main()
