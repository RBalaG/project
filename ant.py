#!/usr/bin/python3
import serial
import time
from datetime import datetime

# --------------------------
# Configuration
# --------------------------
GPS_PORT = "/dev/ttyAMA1"   # GPS connected to LoRa UART header
LORA_PORT = "/dev/ttyAMA0"  # LoRa directly mounted on Raspberry Pi
BAUD_RATE = 9600

# --------------------------
# Open Serial Connections
# --------------------------
try:
    gps = serial.Serial(GPS_PORT, baudrate=BAUD_RATE, timeout=1)
    print(f"[INFO] Connected to GPS module on {GPS_PORT}")
except Exception as e:
    print(f"[ERROR] Could not open GPS port {GPS_PORT}: {e}")
    exit(1)

try:
    lora = serial.Serial(LORA_PORT, baudrate=BAUD_RATE, timeout=1)
    print(f"[INFO] Connected to LoRa module on {LORA_PORT}")
except Exception as e:
    print(f"[ERROR] Could not open LoRa port {LORA_PORT}: {e}")
    exit(1)

# --------------------------
# GPS Parser
# --------------------------
def parse_gpgga(sentence):
    """Extract latitude and longitude from GPGGA sentence"""
    try:
        parts = sentence.split(',')
        if parts[0] == "$GPGGA" and len(parts) > 5 and parts[2] and parts[4]:
            # Latitude
            lat_raw = parts[2]
            lat_dir = parts[3]
            lon_raw = parts[4]
            lon_dir = parts[5]

            lat = float(lat_raw[:2]) + float(lat_raw[2:]) / 60.0
            if lat_dir == 'S':
                lat = -lat

            lon = float(lon_raw[:3]) + float(lon_raw[3:]) / 60.0
            if lon_dir == 'W':
                lon = -lon

            return round(lat, 6), round(lon, 6)
    except:
        return None
    return None

# --------------------------
# Main Loop
# --------------------------
print("[INFO] Starting GPS → LoRa transmission...\n")
try:
    while True:
        gps_line = gps.readline().decode('utf-8', errors='replace').strip()

        if gps_line.startswith("$GPGGA"):
            coords = parse_gpgga(gps_line)
            if coords:
                lat, lon = coords
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"{timestamp} | LAT:{lat} LON:{lon}"

                # Send to LoRa
                lora.write((message + "\n").encode('utf-8'))
                lora.flush()

                print(f"[SENT] {message}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[INFO] Transmission stopped by user.")
finally:
    gps.close()
    lora.close()
    print("[INFO] Serial ports closed.")
