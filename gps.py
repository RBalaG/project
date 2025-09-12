#!/usr/bin/env python3

import serial
import time
import spidev
import RPi.GPIO as GPIO
import subprocess
import json
from datetime import datetime

# LoRa SX1268 Configuration
LORA_CS_PIN = 8
LORA_RST_PIN = 25
LORA_DIO0_PIN = 24
LORA_FREQUENCY = 868000000  # Adjust based on your region

class LoRaSX1268:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.setup_gpio()
        self.setup_spi()
        
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LORA_CS_PIN, GPIO.OUT)
        GPIO.setup(LORA_RST_PIN, GPIO.OUT)
        GPIO.setup(LORA_DIO0_PIN, GPIO.IN)
        
        GPIO.output(LORA_CS_PIN, GPIO.HIGH)
        GPIO.output(LORA_RST_PIN, GPIO.HIGH)
        
    def setup_spi(self):
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1000000
        self.spi.mode = 0
        
    def reset(self):
        GPIO.output(LORA_RST_PIN, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(LORA_RST_PIN, GPIO.HIGH)
        time.sleep(0.05)
        
    def write_register(self, address, value):
        GPIO.output(LORA_CS_PIN, GPIO.LOW)
        self.spi.xfer2([address | 0x80, value])
        GPIO.output(LORA_CS_PIN, GPIO.HIGH)
        
    def read_register(self, address):
        GPIO.output(LORA_CS_PIN, GPIO.LOW)
        response = self.spi.xfer2([address & 0x7F, 0x00])
        GPIO.output(LORA_CS_PIN, GPIO.HIGH)
        return response[1]
        
    def setup_lora(self):
        self.reset()
        
        # Set to sleep mode
        self.write_register(0x01, 0x00)
        
        # Set frequency
        frf = int((LORA_FREQUENCY << 19) / 32000000)
        self.write_register(0x06, (frf >> 16) & 0xFF)
        self.write_register(0x07, (frf >> 8) & 0xFF)
        self.write_register(0x08, frf & 0xFF)
        
        # PA config
        self.write_register(0x09, 0xFF)
        self.write_register(0x0A, 0x09)
        
        # LNA config
        self.write_register(0x0C, 0x23)
        
        # Set to transmit mode
        self.write_register(0x01, 0x83)
        
    def send_data(self, data):
        # Convert data to bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # Set payload length
        self.write_register(0x22, len(data))
        
        # Write data to FIFO
        GPIO.output(LORA_CS_PIN, GPIO.LOW)
        self.spi.xfer2([0x80] + list(data))
        GPIO.output(LORA_CS_PIN, GPIO.HIGH)
        
        # Start transmission
        self.write_register(0x01, 0x83)
        
        # Wait for transmission complete
        while GPIO.input(LORA_DIO0_PIN) == 0:
            time.sleep(0.1)
            
        print(f"Data sent: {data}")

class GPSReader:
    def __init__(self, port='/dev/ttyS0', baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        
    def read_gps_data(self):
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('$GPGGA'):
                return self.parse_gpgga(line)
        except Exception as e:
            print(f"GPS read error: {e}")
            return None
            
    def parse_gpgga(self, data):
        parts = data.split(',')
        if len(parts) >= 10 and parts[6] != '0':  # Fix quality > 0
            return {
                'time': parts[1],
                'latitude': self.convert_coordinate(parts[2], parts[3]),
                'longitude': self.convert_coordinate(parts[4], parts[5]),
                'fix_quality': parts[6],
                'satellites': parts[7],
                'altitude': parts[9],
                'timestamp': datetime.utcnow().isoformat()
            }
        return None
        
    def convert_coordinate(self, coord, direction):
        if not coord or coord == '':
            return 0.0
            
        # Convert DDMM.MMMM to decimal degrees
        degrees = float(coord[:2])
        minutes = float(coord[2:])
        decimal = degrees + (minutes / 60.0)
        
        if direction in ['S', 'W']:
            decimal = -decimal
            
        return round(decimal, 6)

def main():
    print("Initializing GPS and LoRa...")
    
    # Initialize GPS
    gps = GPSReader()
    
    # Initialize LoRa
    lora = LoRaSX1268()
    lora.setup_lora()
    
    print("System ready. Waiting for GPS fix...")
    
    try:
        while True:
            # Read GPS data
            gps_data = gps.read_gps_data()
            
            if gps_data:
                # Convert to JSON string
                json_data = json.dumps(gps_data)
                print(f"GPS Data: {json_data}")
                
                # Send via LoRa
                lora.send_data(json_data)
                
                # Wait before next transmission
                time.sleep(30)  # Send every 30 seconds
            else:
                print("Waiting for GPS fix...")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        GPIO.cleanup()
        if hasattr(gps, 'ser'):
            gps.ser.close()

if __name__ == "__main__":
    main()
