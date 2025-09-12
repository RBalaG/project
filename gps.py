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
LORA_BAUDRATE = 9600
GPS_BAUDRATE = 9600
LORA_PORT = "/dev/serial0"  # SX1262 HAT
GPS_PORT = "/dev/serial0"   # Same UART for GPS (direct pins)

SEND_INTERVAL = 2.0  # Send every 2 seconds

# GPIO pins for LEDs
LED_TX = 17  # GPIO17 (Pin 11)
LED_RX = 27  # GPIO27 (Pin 13)

# ===============================
# LoRa UART Class
# ===============================
class SX126x:
    def __init__(self, port=LORA_PORT, baudrate=LORA_BAUDRATE):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.ser.flushInput()
            print(f"[INFO] LoRa connected to {port} at {baudrate} baud")
        except serial.SerialException as e:
            print(f"[FATAL] Failed to open {port}: {e}")
            sys.exit(1)

    def send(self, data):
        """Send data to LoRa module"""
        try:
            self.ser.write(data.encode())
            GPIO.output(LED_TX, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(LED_TX, GPIO.LOW)
            return True
        except serial.SerialException as e:
            print(f"[ERROR] UART write failed: {e}")
            return False

    def receive(self):
        """Receive data from LoRa module"""
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    GPIO.output(LED_RX, GPIO.HIGH)
                    time.sleep(0.05)
                    GPIO.output(LED_RX, GPIO.LOW)
                    return data
            return None
        except serial.SerialException as e:
            print(f"[ERROR] UART read failed: {e}")
            return None

    def close(self):
        self.ser.close()
        print("[INFO] LoRa serial port closed.")

# ===============================
# GPS Reader
# ===============================
class GPSModule:
    def __init__(self, port=GPS_PORT, baudrate=GPS_BAUDRATE):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"[INFO] GPS connected on {port} at {baudrate} baud")
        except serial.SerialException as e:
            print(f"[FATAL] GPS module not found: {e}")
            sys.exit(1)

    def read_location(self):
        """Read and parse NMEA sentences to get latitude and longitude"""
        line = self.ser.readline().decode('utf-8', errors='ignore').strip()

        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            data = line.split(",")
            if line.startswith("$GPGGA") and len(data) > 5 and data[2] and data[4]:
                lat = self._convert_to_degrees(data[2])
                lon = self._convert_to_degrees(data[4])
                if data[3] == "S":
                    lat = -lat
                if data[5] == "W":
                    lon = -lon
                return lat, lon
        return None

    def _convert_to_degrees(self, raw_value):
        """Convert raw GPS NMEA value to decimal degrees"""
        try:
            degrees = float(raw_value[:2])
            minutes = float(raw_value[2:])
            return degrees + (minutes / 60.0)
        except:
            return 0.0

# ===============================
# Receiver Thread
# ===============================
def receiver_thread(lora):
    print("[INFO] Receiver thread started, listening for packets...\n")
    while True:
        data = lora.receive()
        if data:
            print(f"[RX] {datetime.now().strftime('%H:%M:%S')} -> {data}")

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

    print("===============================================")
    print(" LoRa + Neo-6M GPS Sender (Raspberry Pi) ")
    print("===============================================\n")

    # Initialize devices
    lora = SX126x()
    gps = GPSModule()

    # Start LoRa receiver in background
    threading.Thread(target=receiver_thread, args=(lora,), daemon=True).start()

    print("Press Ctrl+C to stop.\n")
    count = 1

    try:
        while True:
            location = gps.read_location()
            if location:
                lat, lon = location
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"[{count}] {timestamp} LAT:{lat:.6f}, LON:{lon:.6f}"

                # Send GPS data via LoRa
                lora.send(msg + "\n")
                print(f"[TX] Sent GPS: {msg}")

                count += 1
            else:
                print("[WARN] Waiting for valid GPS signal...")

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Exiting gracefully...")
        lora.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
