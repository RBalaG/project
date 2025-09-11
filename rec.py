#!/usr/bin/python
# -- coding: UTF-8 --

import time
import serial
import threading

class sx126x:
    start_freq = 850
    offset_freq = 18

    def __init__(self, serial_num, freq, addr, power, rssi):
        self.addr = addr
        self.freq = freq
        self.power = power
        self.rssi = rssi
        self.serial_n = serial_num
        self.ser = serial.Serial(serial_num, 9600, timeout=0.5)
        self.ser.flushInput()

    def receive(self):
        if self.ser.in_waiting > 0:
            r_buff = self.ser.read(self.ser.in_waiting)
            if len(r_buff) <= 6:  # Check buffer length before slicing
                return
            # Extract only the message payload
            message_bytes = r_buff[6:]  # Skip first 6 bytes
            message = message_bytes.decode(errors='ignore')
            if message.strip() != "":
                print(message)

    def free_serial(self):
        self.ser.close()


# Configure receiver laptop to COM4
node = sx126x(serial_num="dev/ttyAMA0", freq=868, addr=0, power=22, rssi=False)

def receive_loop():
    while True:
        try:
            node.receive()
            time.sleep(0.1)
        except:
            break

threading.Thread(target=receive_loop, daemon=True).start()

print("LoRa Receiver Interface (COM4)")
print("Listening for incoming messages...")
print("Press Ctrl+C to exit")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
    node.free_serial()
