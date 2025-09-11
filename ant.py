#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime

# ===============================
# CONFIGURATION
# ===============================
LORA_SERIAL_PORT = "/dev/serial0"   # Pi UART for LoRa
GPS_SERIAL_PORT = "/dev/ttyUSB0"    # GPS module UART (change if different)
BAUD_LORA = 9600
BAUD_GPS = 9600
SEND_INTERVAL = 1.0  # seconds

# ===============================
# LoRa Class
# ===============================
class SX126x:
    def __init__(self, serial_port=LORA_SERIAL_PORT, baudrate=9600):
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        self.ser.flushInput()
        print(f"[INFO] LoRa serial open: {serial_port} at {baudrate} baud")

    def send(self, data):
        try:
            self.ser.write(data.encode('utf-8') + b'\n')
            self.ser.flush()
            return True
        except serial.SerialException as e:
            print(f"[ERROR] LoRa send failed: {e}")
            return False

    def close(self):
        self.ser.close()
        print("[INFO] LoRa serial closed")

# ===============================
# GPS Class
# ===============================
class GPSModule:
    def __init__(self, serial_port=GPS_SERIAL_PORT, baudrate=9600):
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        self.ser.flushInput()
        print(f"[INFO] GPS serial open: {serial_port} at {baudrate} baud")

    def read(self):
        """Read NMEA sentence from GPS"""
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
                return line
        except serial.SerialException as e:
            print(f"[ERROR] GPS read failed: {e}")
        return None

    def close(self):
        self.ser.close()
        print("[INFO] GPS serial closed")

# ===============================
# Main Logic
# ===============================
def main():
    lora = SX126x()
    gps = GPSModule()

    print("LoRa + GPS Sender")
    print("Sending GPS data over LoRa every second...\n")

    count = 1
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            gps_data = gps.read()

            if gps_data:
                msg = f"[{count}] {timestamp} - GPS: {gps_data}"
            else:
                msg = f"[{count}] {timestamp} - GPS: No fix"

            if lora.send(msg):
                print(f"[TX] {msg}")
            else:
                print("[ERROR] Failed to send message")

            count += 1
            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Exiting gracefully...")
        lora.close()
        gps.close()

if __name__ == "__main__":
    main()
