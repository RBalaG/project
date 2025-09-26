#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
import threading
from datetime import datetime
import os
import sys
import RPi.GPIO as GPIO

# ===============================
# CONFIGURATION
# ===============================
BAUDRATE_LORA = 9600
BAUDRATE_GPS = 9600
SERIAL_PORTS_LORA = ["/dev/serial0", "/dev/ttyAMA0"]  # LoRa
GPS_PORT = "/dev/ttyUSB0"                               # GPS
SEND_INTERVAL = 2.0

LED_TX = 17
LED_RX = 27

# ===============================
# LoRa UART Class
# ===============================
class SX126x:
    def __init__(self, baudrate=9600):
        self.ser = None
        self.baudrate = baudrate
        for port in SERIAL_PORTS_LORA:
            if os.path.exists(port):
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=1)
                    self.ser.flushInput()
                    print(f"[INFO] Connected to LoRa at {port}")
                    break
                except serial.SerialException as e:
                    print(f"[ERROR] Failed to open {port}: {e}")
        if self.ser is None:
            print("[FATAL] No LoRa serial port available!")
            sys.exit(1)

    def send(self, data):
        try:
            bytes_written = self.ser.write(data.encode())
            GPIO.output(LED_TX, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(LED_TX, GPIO.LOW)
            return bytes_written
        except Exception as e:
            print(f"[ERROR] LoRa send failed: {e}")
            return 0

    def close(self):
        if self.ser:
            self.ser.close()
            print("[INFO] LoRa port closed.")

# ===============================
# GPS Reader
# ===============================
class GPSReader:
    def __init__(self, port=GPS_PORT, baudrate=9600):
        try:
            self.gps_ser = serial.Serial(port, baudrate, timeout=1)
            print(f"[INFO] Connected to GPS at {port}")
        except Exception as e:
            print(f"[ERROR] GPS not found: {e}")
            sys.exit(1)

    def parse_lat_lon(self, nmea_sentence):
        """Parse NMEA sentence manually to get latitude and longitude"""
        parts = nmea_sentence.split(",")
        if nmea_sentence.startswith("$GPGGA") and len(parts) > 5:
            # Latitude
            lat_raw = parts[2]
            lat_dir = parts[3]
            lon_raw = parts[4]
            lon_dir = parts[5]
            if lat_raw and lon_raw:
                lat = float(lat_raw[:2]) + float(lat_raw[2:]) / 60
                if lat_dir == "S":
                    lat = -lat
                lon = float(lon_raw[:3]) + float(lon_raw[3:]) / 60
                if lon_dir == "W":
                    lon = -lon
                return round(lat, 6), round(lon, 6)
        return None

    def get_coordinates(self):
        try:
            line = self.gps_ser.readline().decode("utf-8", errors="ignore").strip()
            return self.parse_lat_lon(line)
        except Exception:
            return None

# ===============================
# GPIO Setup
# ===============================
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_TX, GPIO.OUT)
    GPIO.setup(LED_RX, GPIO.OUT)
    GPIO.output(LED_TX, GPIO.LOW)
    GPIO.output(LED_RX, GPIO.LOW)

# ===============================
# Main Logic
# ===============================
def main():
    setup_gpio()
    lora = SX126x(baudrate=BAUDRATE_LORA)
    gps = GPSReader(port=GPS_PORT, baudrate=BAUDRATE_GPS)

    print("=== GPS → LoRa Sender ===\n")
    count = 1
    try:
        while True:
            coords = gps.get_coordinates()
            if coords:
                lat, lon = coords
                msg = f"[{count}] Lat: {lat}, Lon: {lon}, Time: {datetime.now().strftime('%H:%M:%S')}"
                bytes_written = lora.send(msg + "\n")
                print(f"[TX] {msg} ({bytes_written} bytes)")
                count += 1
            else:
                print("[WARN] Waiting for GPS fix...")
            time.sleep(SEND_INTERVAL)
    except KeyboardInterrupt:
        print("\n[INFO] Exiting...")
        lora.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
