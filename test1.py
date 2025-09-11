#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import time
import serial
import serial.tools.list_ports


class sx126x:
    start_freq = 850
    offset_freq = 18

    def __init__(self, serial_num, addr, power):
        self.addr = addr
        try:
            self.ser = serial.Serial(serial_num, 9600, timeout=0.5)
            self.ser.flushInput()
            print(f"[OK] Connected to {serial_num}")
        except Exception as e:
            print(f"[ERROR] Could not open serial port {serial_num}: {e}")
            exit(1)

    def send(self, data):
        self.ser.write(data)
        time.sleep(0.1)

    def free_serial(self):
        self.ser.close()


def auto_detect_port():
    """Auto-detect first available serial port (USB or GPIO)."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "USB" in p.device or "AMA" in p.device or "serial" in p.device:
            return p.device
    return None


# --- Main program ---
print("LoRa Sender Interface on Raspberry Pi")

port = auto_detect_port()
if not port:
    print("❌ No LoRa device found. Please check connection.")
    exit(1)

node = sx126x(serial_num=port, addr=0, power=22)

print("✅ Ready! Type messages in format: dest_addr,freq,message")
print("Press Ctrl+C to exit")

try:
    while True:
        user_input = input("\nSend: ").strip()
        if not user_input:
            continue
        try:
            parts = user_input.split(",", 2)  # ensure only 3 parts max
            if len(parts) != 3:
                print("❌ Invalid format! Use: dest_addr,freq,message")
                continue

            # validate numbers
            try:
                dest_addr = int(parts[0])
                freq = int(parts[1])
            except ValueError:
                print("❌ dest_addr and freq must be numbers!")
                continue

            msg = parts[2]

            offset_freq = freq - (850 if freq > 850 else 410)
            data = bytes([
                dest_addr >> 8, dest_addr & 0xFF, offset_freq,
                node.addr >> 8, node.addr & 0xFF, node.offset_freq
            ]) + msg.encode()

            node.send(data)
            print("✅ Message sent!")

        except Exception as e:
            print("⚠️ Error sending message:", e)

except KeyboardInterrupt:
    print("\nExiting...")
    node.free_serial()
