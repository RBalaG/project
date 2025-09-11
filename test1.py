#!/usr/bin/python
# -*- coding: UTF-8 -*-

import time
import serial

class sx126x:
    start_freq = 850
    offset_freq = 18

    def __init__(self, serial_num, addr, power):
        self.addr = addr
        self.ser = serial.Serial(serial_num, 9600, timeout=0.5)
        self.ser.flushInput()

    def send(self, data):
        self.ser.write(data)
        time.sleep(0.1)

    def free_serial(self):
        self.ser.close()


# Configure sender laptop
node = sx126x(serial_num="COM5", addr=0, power=22)

print("LoRa Sender Interface")
print("Type messages in format: dest_addr,freq,message")
print("Press Ctrl+C to exit")

try:
    while True:
        user_input = input("\nSend: ")
        if user_input.strip() == "":
            continue
        try:
            parts = user_input.split(",")
            dest_addr = int(parts[0])
            freq = int(parts[1])
            msg = parts[2]

            offset_freq = freq - (850 if freq > 850 else 410)
            data = bytes([dest_addr >> 8, dest_addr & 0xFF, offset_freq,
                          node.addr >> 8, node.addr & 0xFF, node.offset_freq]) + msg.encode()
            node.send(data)
            print("Message sent!")
        except Exception as e:
            print("Error sending message:", e)

except KeyboardInterrupt:
    print("\nExiting...")
    node.free_serial()
