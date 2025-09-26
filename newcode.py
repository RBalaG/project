#!/usr/bin/python3
import serial
import time

# LoRa HAT port (check with: ls -l /dev/serial*)
LORA_PORT = "/dev/serial0"
LORA_BAUDRATE = 9600

# Open LoRa serial
lora = serial.Serial(LORA_PORT, LORA_BAUDRATE, timeout=1)
print(f"[ OK ] LoRa opened on {LORA_PORT} at {LORA_BAUDRATE} baud")

count = 0
while True:
    msg = f"Hello LoRa #{count}"
    lora.write((msg + "\n").encode())
    print("[SENT]", msg)
    count += 1
    time.sleep(2)
