#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime
import os
import sys
import RPi.GPIO as GPIO

# ===============================
# CONFIGURATION
# ===============================
LORA_PORTS = ["/dev/serial0", "/dev/ttyAMA0"]  # LoRa connected to Pi GPIO UART
GPS_PORT = "/dev/ttyUSB0"  # Neo-6M GPS (via USB-UART adapter)
LORA_BAUDRATE = 9600
GPS_BAUDRATE = 9600
SEND_INTERVAL = 2.0  # seconds

# GPIO pins for LEDs
LED_TX = 17  # GPIO17 (Pin 11)

# ===============================
# GPIO Setup
# ===============================
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_TX, GPIO.OUT)
    GPIO.output(LED_TX, GPIO.LOW)

# ===============================
# LoRa UART Class
# ===============================
class SX126x:
    def __init__(self, baudrate=9600):
        self.ser = None
        for port in LORA_PORTS:
            if os.path.exists(port):
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=1)
                    self.ser.flushInput()
                    print(f"[INFO] LoRa connected on {port}")
                    break
                except serial.SerialException as e:
                    print(f"[ERROR] Cannot open {port}: {e}")
        if self.ser is None:
            print("[FATAL] No LoRa port found. Exiting...")
            sys.exit(1)

    def send(self, data):
        try:
            self.ser.write(data.encode())
            GPIO.output(LED_TX, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(LED_TX, GPIO.LOW)
        except Exception as e:
            print(f"[ERROR] LoRa send failed: {e}")

# ===============================
# GPS Reader
# ===============================
class GPSModule:
    def __init__(self, port, baudrate=9600):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"[INFO] GPS connected on {port}")
        except serial.SerialException as e:
            print(f"[FATAL] GPS not found: {e}")
            sys.exit(1)

    def read_location(self):
        line = self.ser.readline().decode("utf-8", errors="ignore").strip()
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            data = line.split(",")
            # GPGGA fix
            if line.startswith("$GPGGA") and len(data) > 5 and data[2] and data[4]:
                lat = self._convert_to_degrees(data[2])
                lon = self._convert_to_degrees(data[4])
                if data[3] == "S": lat = -lat
                if data[5] == "W": lon = -lon
                if data[6] != "0":  # valid fix
                    return lat, lon
            # GPRMC fix
            elif line.startswith("$GPRMC") and len(data) > 6 and data[3] and data[5]:
                lat = self._convert_to_degrees(data[3])
                lon = self._convert_to_degrees(data[5])
                if data[4] == "S": lat = -lat
                if data[6] == "W": lon = -lon
                if data[2] == "A":  # active
                    return lat, lon
        return None

    def _convert_to_degrees(self, raw_value):
        try:
            raw_value = float(raw_value)
            degrees = int(raw_value / 100)
            minutes = raw_value - (degrees * 100)
            return degrees + (minutes / 60.0)
        except:
            return 0.0

# ===============================
# Main
# ===============================
def main():
    setup_gpio()
    print("=====================================")
    print("   Raspberry Pi GPS → LoRa Sender    ")
    print("=====================================\n")

    lora = SX126x(baudrate=LORA_BAUDRATE)
    gps = GPSModule(port=GPS_PORT, baudrate=GPS_BAUDRATE)

    count = 1
    try:
        while True:
            location = gps.read_location()
            if location:
                lat, lon = location
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"[{count}] {timestamp} LAT:{lat:.6f}, LON:{lon:.6f}"
                lora.send(msg + "\n")
                print(f"[TX] {msg}")
                count += 1
            else:
                print("[WARN] Waiting for GPS fix...")
            time.sleep(SEND_INTERVAL)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
