#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime
import sys

class sx126x:
    def __init__(self, serial_port="/dev/serial0", baudrate=9600):
        # Open the Raspberry Pi serial port
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        self.ser.flushInput()
        print(f"Serial port {serial_port} opened at {baudrate} baud.")

    def send(self, data):
        """Send data to the LoRa module"""
        self.ser.write(data.encode('utf-8'))
        self.ser.flush()
        time.sleep(0.05)  # Short wait for TX

    def free_serial(self):
        """Close serial port"""
        self.ser.close()
        print("Serial port closed.")

    def use_external_antenna(self):
        """Log message for IPEX antenna usage"""
        print("📡 External IPEX antenna selected. Transmission will use this port.")

    def use_internal_antenna(self):
        """Log message for onboard PCB antenna usage"""
        print("📡 Internal PCB antenna selected. Transmission will use this port.")

# --- Runtime Antenna Selection ---
antenna = "ipex"
if len(sys.argv) > 1:
    antenna = sys.argv[1].lower()

# Create LoRa node using Pi's UART
node = sx126x(serial_port="/dev/serial0", baudrate=9600)

if antenna == "ipex":
    node.use_external_antenna()
else:
    node.use_internal_antenna()

print("LoRa Continuous Sender (Raspberry Pi Direct Mount)")
print("Sending message every 1 second... (Press Ctrl+C to stop)\n")

try:
    count = 1
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{count}] {timestamp} - Hello LoRa"
        node.send(msg)
        print(f"Sent: {msg}")
        count += 1
        time.sleep(1)  # send every 1 second

except KeyboardInterrupt:
    node.free_serial()
    print("\nExiting...")
