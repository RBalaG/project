#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import serial
import serial.tools.list_ports
import time


class LoRaReceiver:
    def __init__(self, serial_port, baudrate=9600, addr=1):  # Pi as receiver addr=1
        self.addr = addr
        try:
            self.ser = serial.Serial(serial_port, baudrate=baudrate, timeout=1)
            print(f"[OK] Connected to {serial_port}")
        except Exception as e:
            print(f"[ERROR] Could not open serial port {serial_port}: {e}")
            exit(1)

    def receive(self):
        """Continuously listen for messages."""
        while True:
            if self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode(errors='ignore').strip()
                    if line:
                        if ":" in line:
                            src_addr, msg = line.split(":", 1)
                            print(f"\n📩 From {src_addr}: {msg}")
                        else:
                            print(f"\n📩 Received: {line}")
                except Exception as e:
                    print(f"[ERROR] Decoding message: {e}")
            time.sleep(0.1)

    def close(self):
        self.ser.close()


def detect_lora_port():
    """Auto-detect LoRa serial port (USB or GPIO)."""
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if ("USB" in port.device) or ("AMA" in port.device) or ("serial" in port.device):
            print(f"Detected LoRa module on {port.device}")
            return port.device
    raise Exception("No LoRa module detected! Check connection.")


# --- Main program ---
print("LoRa Receiver Interface on Raspberry Pi")

port = detect_lora_port()
receiver = LoRaReceiver(serial_port=port, addr=1)

print("✅ Ready! Listening for messages (Press Ctrl+C to stop)...")

try:
    receiver.receive()
except KeyboardInterrupt:
    print("\nExiting...")
    receiver.close()

