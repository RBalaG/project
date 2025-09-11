#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime

class sx126x:
    def __init__(self, serial_port="/dev/serial0", baudrate=9600):
        try:
            self.ser = serial.Serial(serial_port, baudrate, timeout=1)
            self.ser.flushInput()
            print(f"Serial port {serial_port} opened at {baudrate} baud.")
        except Exception as e:
            print(f"Error opening serial port: {e}")
            exit(1)

    def send(self, data):
        """Send data to the LoRa module"""
        try:
            self.ser.write(data.encode('utf-8'))
            self.ser.flush()
            print(f"Sent: {data}")
        except Exception as e:
            print(f"Error sending data: {e}")

    def free_serial(self):
        self.ser.close()
        print("Serial port closed.")

# Main
if __name__ == "__main__":
    node = sx126x("/dev/serial0", 9600)
    count = 1
    print("LoRa Continuous Sender (Raspberry Pi Direct Mount)")
    print("Sending message every 1 second... (Press Ctrl+C to stop)\n")

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"[{count}] {timestamp} - Hello LoRa"
            node.send(message)
            count += 1
            time.sleep(1)
    except KeyboardInterrupt:
        node.free_serial()
        print("\nExiting...")
