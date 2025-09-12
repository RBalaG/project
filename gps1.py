#!/usr/bin/python3
import time
import serial
import threading
from datetime import datetime
import os
import sys
import RPi.GPIO as GPIO

# CONFIG
LORA_BAUDRATE = 9600
GPS_BAUDRATE = 9600
LORA_PORTS = ["/dev/serial0", "/dev/ttyAMA0"]
GPS_PORT = "/dev/serial0"
SEND_INTERVAL = 2.0

LED_TX = 17
LED_RX = 27

# LoRa Class
class SX126x:
    def __init__(self, baudrate=9600):
        self.ser = None
        for port in LORA_PORTS:
            if os.path.exists(port):
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=1)
                    self.ser.flushInput()
                    print(f"[INFO] LoRa connected to {port}")
                    break
                except:
                    pass
        if not self.ser:
            print("[FATAL] No LoRa serial port")
            sys.exit(1)

    def send(self, data):
        try:
            self.ser.write(data.encode())
            GPIO.output(LED_TX, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(LED_TX, GPIO.LOW)
        except:
            pass

# GPS Class
class GPSModule:
    def __init__(self, port, baudrate=9600):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print("[INFO] GPS connected")
        except:
            print("[FATAL] GPS not found")
            sys.exit(1)

    def read_location(self):
        line = self.ser.readline().decode(errors='ignore').strip()
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            return line  # For testing, we return raw NMEA
        return None

# GPIO Setup
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_TX, GPIO.OUT)
    GPIO.setup(LED_RX, GPIO.OUT)
    GPIO.output(LED_TX, GPIO.LOW)
    GPIO.output(LED_RX, GPIO.LOW)

# Main
def main():
    setup_gpio()
    lora = SX126x()
    gps = GPSModule(GPS_PORT)

    count = 1
    try:
        while True:
            location = gps.read_location()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if location:
                msg = f"[{count}] {timestamp} GPS_RAW:{location}"
            else:
                msg = f"[{count}] {timestamp} GPS_FIX_NOT_YET"

            lora.send(msg + "\n")
            print(msg)
            count += 1
            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Exiting...")

if __name__ == "__main__":
    main()
