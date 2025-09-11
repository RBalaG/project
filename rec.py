#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import time
import serial
import serial.tools.list_ports


class sx126x:
    def __init__(self, serial_num, addr, power):
        self.addr = addr
        try:
            self.ser = serial.Serial(serial_num, 9600, timeout=0.5)
            self.ser.flushInput()
            print(f"[OK] Connected to {serial_num}")
        except Exception as e:
            print(f"[ERROR] Could not open serial port {serial_num}: {e}")
            exit(1)

    def receive(self):
        if self.ser.in_waiting:
            data = self.ser.read(self.ser.in_waiting)
            return data
        return None

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
print("LoRa Receiver Interface on Raspberry Pi")

port = auto_detect_port()
if not port:
    print("❌ No LoRa device found. Please check connection.")
    exit(1)

node = sx126x(serial_num=port, addr=1, power=22)  # addr=1 for receiver node

print("✅ Ready! Waiting for messages...")
print("Press Ctrl+C to exit")

try:
    while True:
        data = node.receive()
        if data:
            try:
                # First 6 bytes are header: dest_addr_hi, dest_addr_lo, offset_freq, src_addr_hi, src_addr_lo, src_offset
                if len(data) >= 6:
                    dest_addr = (data[0] << 8) | data[1]
                    offset_freq = data[2]
                    src_addr = (data[3] << 8) | data[4]
                    msg = data[6:].decode(errors="ignore")

                    print("\n📩 Received Message:")
                    print(f"   From: {src_addr}")
                    print(f"   To: {dest_addr}")
                    print(f"   Freq Offset: {offset_freq}")
                    print(f"   Message: {msg}")
                else:
                    print("⚠️ Received incomplete data:", data)
            except Exception as e:
                print("⚠️ Error decoding message:", e)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")
    node.free_serial()
