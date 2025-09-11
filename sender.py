#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
import threading
from datetime import datetime
import os
import sys
import logging
import RPi.GPIO as GPIO

# ===============================
# CONFIGURATION
# ===============================
BAUDRATE = 9600           # Must match LoRa module UART baud rate
SERIAL_PORTS = ["/dev/serial0", "/dev/ttyAMA0"]  # Auto-detect list
SEND_INTERVAL = 1.0       # Seconds between sends
LOG_FILE = "/home/pi/lora_log.txt"

# GPIO pins for TX/RX status LEDs
LED_TX = 17  # GPIO17 for TX indicator
LED_RX = 27  # GPIO27 for RX indicator

# ===============================
# Logging Setup
# ===============================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ===============================
# LoRa UART Class
# ===============================
class SX126x:
    def __init__(self, baudrate=9600):
        self.ser = None
        self.baudrate = baudrate
        self.packets_sent = 0
        self.packets_received = 0
        self.errors = 0

        # Detect and open first available serial port
        for port in SERIAL_PORTS:
            if os.path.exists(port):
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=1)
                    self.ser.flushInput()
                    print(f"[INFO] Connected to {port} at {baudrate} baud")
                    logging.info(f"Connected to {port} at {baudrate} baud")
                    break
                except serial.SerialException as e:
                    print(f"[ERROR] Failed to open {port}: {e}")
                    logging.error(f"Failed to open {port}: {e}")
        
        if self.ser is None:
            print("[FATAL] No serial port available! Exiting...")
            logging.critical("No serial port available! Exiting...")
            sys.exit(1)

    def send(self, data):
        """Send data to LoRa module"""
        try:
            if not self.ser:
                raise serial.SerialException("Serial port not initialized")

            # Ensure data ends with newline
            if not data.endswith("\n"):
                data += "\n"

            bytes_written = self.ser.write(data.encode('utf-8'))
            self.packets_sent += 1

            logging.info(f"TX -> {data.strip()} ({bytes_written} bytes)")
            print(f"[DEBUG] TX Bytes: {bytes_written}")

            # Blink TX LED
            GPIO.output(LED_TX, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(LED_TX, GPIO.LOW)

            return bytes_written
        except serial.SerialException as e:
            self.errors += 1
            print(f"[ERROR] UART write failed: {e}")
            logging.error(f"UART write failed: {e}")
            return 0

    def receive(self):
        """Receive data from LoRa module"""
        try:
            if self.ser and self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    self.packets_received += 1
                    logging.info(f"RX <- {data}")
                    
                    # Blink RX LED
                    GPIO.output(LED_RX, GPIO.HIGH)
                    time.sleep(0.05)
                    GPIO.output(LED_RX, GPIO.LOW)

                    return data
            return None
        except serial.SerialException as e:
            self.errors += 1
            logging.error(f"UART read failed: {e}")
            return None

    def close(self):
        """Close serial connection"""
        if self.ser:
            self.ser.close()
            print("[INFO] Serial port closed.")
            logging.info("Serial port closed")

# ===============================
# Receiver Thread
# ===============================
def receiver_thread(lora):
    """Continuously listens for incoming messages"""
    print("[INFO] Receiver thread started, waiting for data...\n")
    while True:
        data = lora.receive()
        if data:
            print(f"[RX] {datetime.now().strftime('%H:%M:%S')} -> {data}")

# ===============================
# GPIO Setup
# ===============================
def setup_gpio():
    GPIO.setwarnings(False)
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

    lora = SX126x(baudrate=BAUDRATE)

    # Start RX thread
    threading.Thread(target=receiver_thread, args=(lora,), daemon=True).start()

    print("===============================================")
    print(" LoRa Continuous Sender (Raspberry Pi UART)   ")
    print("===============================================\n")
    print("Press Ctrl+C to stop.\n")

    count = 1
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"[{count}] {timestamp} - Hello from Raspberry Pi"
            bytes_written = lora.send(msg)
            print(f"[TX] Sent: {msg} ({bytes_written} bytes)")
            count += 1
            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[INFO] Exiting gracefully...")
        lora.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
