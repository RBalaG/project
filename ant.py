#!/usr/bin/python3
import serial
import pynmea2
import time

# GPS connected via UART (adjust if needed)
gps_port = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)

# LoRa UART (same as before if working)
lora_port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

while True:
    try:
        line = gps_port.readline().decode('ascii', errors='replace')
        if line.startswith('$GNGGA') or line.startswith('$GPGGA'):
            msg = pynmea2.parse(line)
            lat = msg.latitude
            lon = msg.longitude

            gps_data = f"{lat:.6f},{lon:.6f}"
            print("Sending:", gps_data)

            lora_port.write(gps_data.encode('utf-8'))
            lora_port.write(b'\n')   # newline for separation
            time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(1)
