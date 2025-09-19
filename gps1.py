#!/usr/bin/python3
# -- coding: UTF-8 --
"""
GPS -> LoRa sender (dual-mode):
 - Uses SX126x driver (LoRaRF) when available (SPI)
 - Falls back to AT-command mode on a UART if driver missing
Sends messages like:
 2025-09-19 12:00:00 LAT:12.971600 LON:77.594600 SPD:3.42km/h
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
# CONFIGURATION (edit if needed)
# ===============================
# GPS (input) UART
GPS_PORT = "/dev/ttyAMA0"    # GPS serial (change to /dev/serial0 if needed)
GPS_BAUD = 9600

# Optional AT-mode LoRa UART (fallback)
LORA_AT_PORT = "/dev/serial0"  # Many HATs expose an AT UART here
LORA_AT_BAUD = 9600

# LoRa radio parameters (used for driver or sent to AT firmware)
LORA_FREQ = 868000000    # 868 MHz
LORA_BW = 125000         # 125 kHz
LORA_SF = 9              # SF7..SF12 (lower = faster, shorter range; higher = slower, longer range)
LORA_CR = 5              # Representing 4/5 (common library usage)
LORA_POWER = 22          # dBm (use legal limit in your region)

SEND_INTERVAL = 1.0      # seconds between messages

# ===============================
# Utility: Haversine (meters)
# ===============================
def haversine_m(lat1, lon1, lat2, lon2):
    """Return distance between two lat/lon points in meters."""
    R = 6371000.0  # earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# ===============================
# Init GPS serial (input)
# ===============================
def init_gps():
    if not os.path.exists(GPS_PORT):
        print(f"[FATAL] GPS port '{GPS_PORT}' not found. Check wiring and enable UART in raspi-config.")
        sys.exit(1)
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        # flush a bit
        time.sleep(0.5)
        ser.reset_input_buffer()
        print(f"[INFO] GPS connected on {GPS_PORT} @ {GPS_BAUD}")
        return ser
    except serial.SerialException as e:
        print(f"[FATAL] Could not open GPS serial: {e}")
        sys.exit(1)

# ===============================
# LoRa driver (SX126x) initialization
# ===============================
def init_lora_driver():
    """Initialize SX126x via LoRaRF if available. Returns tuple ('sx', obj)."""
    if not HAS_SX126X:
        return None
    try:
        lora = SX126x()
        # begin(...) args depend on the LoRaRF API; this follows common usage
        lora.begin(
            freq=LORA_FREQ,
            bw=LORA_BW,
            sf=LORA_SF,
            cr=LORA_CR,
            syncWord=0x12,
            power=LORA_POWER,
            currentLimit=60.0
        )
        print(f"[INFO] SX126x driver init OK: {LORA_FREQ//1000000}MHz SF{LORA_SF} BW{LORA_BW} CR4/{LORA_CR} P{LORA_POWER}dBm")
        return ('sx', lora)
    except Exception as e:
        print(f"[WARN] SX126x init failed: {e}")
        return None

# ===============================
# LoRa AT-mode initialization (UART)
# ===============================
def init_lora_at():
    """Open AT-mode serial to LoRa module and configure parameters via AT commands.
       Returns tuple ('at', serial_instance)."""
    if not os.path.exists(LORA_AT_PORT):
        print(f"[WARN] AT-mode port '{LORA_AT_PORT}' not found. Skipping AT fallback.")
        return None
    try:
        at = serial.Serial(LORA_AT_PORT, LORA_AT_BAUD, timeout=1)
        time.sleep(0.5)
        at.reset_input_buffer()
        print(f"[INFO] LoRa AT serial opened on {LORA_AT_PORT} @ {LORA_AT_BAUD}")
    except serial.SerialException as e:
        print(f"[WARN] Cannot open AT serial: {e}")
        return None

    def at_write(cmd, wait=0.1, show=True):
        try:
            at.write((cmd + "\r\n").encode())
            time.sleep(wait)
            resp = at.read_all().decode(errors='ignore').strip()
            if show:
                print(f"[AT] {cmd} -> {resp}")
            return resp
        except Exception as ex:
            print(f"[ERROR] AT write failed: {ex}")
            return ""

    # Basic check + configure parameters (these commands vary by firmware vendor)
    # Many EU/Chinese HAT firmware accept AT+FREQ, AT+SF, AT+BW, AT+CR, AT+POWER
    try:
        at_write("AT")  # simple check; some firmwares reply "OK" or version info
        at_write(f"AT+FREQ={LORA_FREQ}")
        at_write(f"AT+SF={LORA_SF}")        # e.g., SF7, SF9, ...
        # BW often set in kHz for some firmwares (125), others expect Hz (125000). Try common one:
        at_write(f"AT+BW={int(LORA_BW/1000)}")  # send 125 (kHz)
        at_write(f"AT+CR=4/{LORA_CR}")           # some firmwares accept "4/5"
        at_write(f"AT+POWER={LORA_POWER}")
        # Optional: set mode to transparent or LoRa mode if supported:
        # at_write("AT+MODE=LW")
        print("[INFO] AT-mode LoRa configured (best-effort).")
    except Exception as e:
        print(f"[WARN] AT config may have failed: {e}")

    return ('at', at)

# ===============================
# Generic send wrapper
# ===============================
def send_lora(iface, handle, text):
    """Send 'text' over LoRa. iface is 'sx' or 'at'."""
    if iface == 'sx':
        lora = handle
        try:
            # Try common APIs in order for compatibility
            if hasattr(lora, "send"):
                # some LoRaRF libraries expect a string
                lora.send(text)
                return True
            # try packet interface
            if hasattr(lora, "beginPacket") and hasattr(lora, "print") and hasattr(lora, "endPacket"):
                lora.beginPacket()
                lora.print(text)
                lora.endPacket()
                return True
            # try write/send bytes
            if hasattr(lora, "write"):
                lora.write(text.encode())
                return True
            # last resort: try calling send with bytes
            try:
                lora.send(text.encode())
                return True
            except Exception:
                pass
            print("[ERROR] SX126x object does not expose a known send() API.")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to send via SX126x: {e}")
            return False

    elif iface == 'at':
        at = handle
        try:
            # Many AT firmwares accept: AT+SEND=<payload>
            cmd = f"AT+SEND={text}"
            at.write((cmd + "\r\n").encode())
            time.sleep(0.1)
            resp = at.read_all().decode(errors='ignore').strip()
            print(f"[AT SEND] {cmd} -> {resp}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send via AT-mode: {e}")
            return False
    else:
        print("[ERROR] Unknown LoRa interface")
        return False

# ===============================
# Main
# ===============================
def main():
    gps = init_gps()

    # Try SX126x driver first, else AT fallback
    lora_iface = None
    lora_handle = None

    if HAS_SX126X:
        res = init_lora_driver()
        if res:
            lora_iface, lora_handle = res

    if lora_iface is None:
        # try AT fallback
        res = init_lora_at()
        if res:
            lora_iface, lora_handle = res

    if lora_iface is None:
        print("[FATAL] No LoRa interface available. Install LoRaRF or enable AT-mode on the HAT.")
        print(" - To use driver via SPI, install the LoRaRF package or appropriate SX126x python driver.")
        print(" - Or wire up and enable the module's AT-mode UART and set LORA_AT_PORT correctly.")
        sys.exit(1)

    print("======================================")
    print("  GPS -> LoRa sender (dual-mode)")
    print("======================================")

    last_lat = last_lon = last_time = None
    last_fix_valid = False

    try:
        while True:
            try:
                line = gps.readline().decode('ascii', errors='ignore').strip()
            except Exception as e:
                print(f"[WARN] GPS read error: {e}")
                line = ""

            if not line:
                # no data quickly loop
                time.sleep(0.05)
                continue

            # parse only useful NMEA sentences
            if line.startswith("$GPGGA") or line.startswith("$GPRMC") or line.startswith("$GNGGA") or line.startswith("$GNRMC"):
                try:
                    msg = pynmea2.parse(line)
                except pynmea2.ParseError:
                    continue

                # some sentences may not include lat/lon
                if not (hasattr(msg, "latitude") and hasattr(msg, "longitude") and msg.latitude and msg.longitude):
                    last_fix_valid = False
                    continue

                lat = float(msg.latitude)
                lon = float(msg.longitude)

                # derive timestamp from NMEA if available (UTC)
                gps_time = None
                if hasattr(msg, "timestamp") and getattr(msg, "timestamp"):
                    # Combine with today's date (NMEA lacks date in some sentences)
                    now_utc = datetime.utcnow()
                    try:
                        gps_dt = datetime.combine(now_utc.date(), msg.timestamp, tzinfo=timezone.utc)
                        gps_time = gps_dt.timestamp()
                    except Exception:
                        gps_time = None

                current_time = gps_time if gps_time else time.time()

                # speed calculation (m)
                speed_kmh = 0.0
                if last_fix_valid and last_lat is not None and last_lon is not None and last_time is not None:
                    dist_m = haversine_m(last_lat, last_lon, lat, lon)
                    dt = current_time - last_time
                    if dt > 0 and dist_m > 0.5:  # >0.5 m to avoid jitter
                        speed_kmh = (dist_m / dt) * 3.6

                last_lat, last_lon, last_time = lat, lon, current_time
                last_fix_valid = True

                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                payload = f"{timestamp} LAT:{lat:.7f} LON:{lon:.7f} SPD:{speed_kmh:.2f}km/h"

                ok = send_lora(lora_iface, lora_handle, payload)
                if ok:
                    print(f"[TX] {payload}")
                else:
                    print(f"[TX-FAIL] {payload}")

                time.sleep(SEND_INTERVAL)

            # else ignore other NMEA lines

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user, exiting...")

    finally:
        try:
            gps.close()
        except Exception:
            pass
        if lora_iface == 'at' and lora_handle:
            try:
                lora_handle.close()
            except Exception:
                pass

        print("[INFO] Clean exit.")


if __name__ == "__main__":
    main()
