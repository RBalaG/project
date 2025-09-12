#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime

# ----------------------------
# LoRa Class
# ----------------------------
class sx126x:
    def __init__(self, serial_port="/dev/serial0", baudrate=9600):
        """Initialize LoRa serial connection"""
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        self.ser.flushInput()
        print(f"[LoRa] Port {serial_port} opened at {baudrate} baud.")

    def send(self, data):
        """Send data to the LoRa module"""
        self.ser.write(data.encode('utf-8'))
        self.ser.flush()
        time.sleep(0.05)

    def free_serial(self):
        """Close serial port"""
        self.ser.close()
        print("[LoRa] Port closed.")

# ----------------------------
# GPS to Decimal Conversion
# ----------------------------
def convert_to_decimal(raw_val, direction):
    """
    Convert GPS raw data (DDMM.MMMM) to decimal degrees.
    Example: 1234.5678 -> 12 + (34.5678 / 60) = 12.57613
    """
    if raw_val == '' or direction == '':
        return None
    raw_val = float(raw_val)
    degrees = int(raw_val // 100)
    minutes = raw_val % 100
    decimal = degrees + (minutes / 60)
    if direction in ['S', 'W']:
        decimal *= -1
    return round(decimal, 6)

# ----------------------------
# Initialize LoRa and GPS
# ----------------------------
# LoRa connected to Raspberry Pi
lora = sx126x(serial_port="/dev/serial0", baudrate=9600)

# GPS connected to Raspberry Pi
gps = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

print("LoRa + GPS Sender Started...")
print("Sending GPS location every 2 seconds. Press Ctrl+C to stop.\n")

# ----------------------------
# Main Loop
# ----------------------------
try:
    while True:
        line = gps.readline().decode('ascii', errors='replace').strip()

        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            parts = line.split(',')

            if line.startswith("$GPGGA") and len(parts) > 5:
                raw_lat = parts[2]
                lat_dir = parts[3]
                raw_lon = parts[4]
                lon_dir = parts[5]

            elif line.startswith("$GPRMC") and len(parts) > 6:
                raw_lat = parts[3]
                lat_dir = parts[4]
                raw_lon = parts[5]
                lon_dir = parts[6]

            else:
                continue

            latitude = convert_to_decimal(raw_lat, lat_dir)
            longitude = convert_to_decimal(raw_lon, lon_dir)

            if latitude is not None and longitude is not None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                gps_data = f"[{timestamp}] Lat:{latitude}, Lon:{longitude}"

                # Send via LoRa
                lora.send(gps_data)
                print(f"Sent: {gps_data}")
                time.sleep(2)  # send every 2 seconds

except KeyboardInterrupt:
    print("\nExiting...")
    lora.free_serial()
    gps.close()
