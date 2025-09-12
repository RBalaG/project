#!/usr/bin/python3
import time
import serial
from datetime import datetime

# ----------------------------
# LoRa Class
# ----------------------------
class sx126x:
    def __init__(self, serial_port="/dev/serial0", baudrate=9600):
        """Initialize LoRa serial connection"""
        try:
            self.ser = serial.Serial(serial_port, baudrate, timeout=1)
            self.ser.flushInput()
            print(f"[LoRa] Port {serial_port} opened at {baudrate} baud.")
        except Exception as e:
            print(f"[ERROR] Cannot open LoRa port {serial_port}: {e}")
            exit(1)

    def send(self, data):
        """Send data to the LoRa module"""
        self.ser.write((data + "\n").encode('utf-8'))
        self.ser.flush()
        time.sleep(0.05)

    def free_serial(self):
        """Close serial port"""
        self.ser.close()
        print("[LoRa] Port closed.")

# ----------------------------
# GPS Initialization
# ----------------------------
try:
    gps = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)
    print("[GPS] Connected to Neo-6M GPS module on /dev/ttyAMA0")
except Exception as e:
    print(f"[ERROR] Cannot open GPS port: {e}")
    exit(1)

# ----------------------------
# LoRa Initialization
# ----------------------------
lora = sx126x(serial_port="/dev/serial0", baudrate=9600)

print("\n[INFO] LoRa + GPS Sender Started")
print("Sending GPS data every 2 seconds. Press Ctrl+C to stop.\n")

# ----------------------------
# Helper Function: Parse GPS
# ----------------------------
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

# ----------------------------
# Main Loop
# ----------------------------
try:
    while True:
        line = gps.readline().decode('utf-8', errors='replace').strip()

        if line.startswith("$GPGGA"):
            coords = parse_gpgga(line)
            if coords:
                lat, lon = coords
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"[{timestamp}] LAT:{lat}, LON:{lon}"

                # Send data via LoRa
                lora.send(message)
                print(f"[SENT] {message}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\n[INFO] Stopping sender...")
    gps.close()
    lora.free_serial()
