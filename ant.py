#!/usr/bin/python3
# -- coding: UTF-8 --

import time
import serial
from datetime import datetime
import pynmea2  # For parsing GPS NMEA data

# ----------------------------
# LoRa Class
# ----------------------------
class sx126x:
    def __init__(self, serial_port="/dev/serial0", baudrate=9600):
        self.ser = serial.Serial(serial_port, baudrate, timeout=1)
        self.ser.flushInput()
        print(f"[LoRa] Port {serial_port} opened at {baudrate} baud.")

    def send(self, data):
        self.ser.write(data.encode('utf-8'))
        self.ser.flush()
        time.sleep(0.05)

    def close(self):
        self.ser.close()
        print("[LoRa] Port closed.")

# ----------------------------
# Initialize LoRa and GPS
# ----------------------------
lora = sx126x(serial_port="/dev/serial0", baudrate=9600)
gps = serial.Serial("/dev/ttyAMA1", baudrate=9600, timeout=1)  # GPS on UART1

print("LoRa + GPS Sender Started...")
print("Sending GPS location every 2 seconds.\n")

# ----------------------------
# Main Loop
# ----------------------------
try:
    while True:
        line = gps.readline().decode('ascii', errors='replace').strip()
        
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            try:
                msg = pynmea2.parse(line)
                if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                    gps_data = f"Lat: {msg.latitude:.6f}, Lon: {msg.longitude:.6f}"
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    final_message = f"[{timestamp}] {gps_data}"
                    
                    # Send via LoRa
                    lora.send(final_message)
                    print(f"Sent: {final_message}")
                    time.sleep(2)
            except pynmea2.ParseError:
                continue

except KeyboardInterrupt:
    lora.close()
    gps.close()
    print("\nExiting...")
