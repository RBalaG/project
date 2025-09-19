import serial
import time

# Open UART (adjust if your port is /dev/ttyS0 or /dev/ttyAMA0)
ser = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)

def send_cmd(cmd, delay=0.5):
    ser.write((cmd + '\r\n').encode())
    time.sleep(delay)
    reply = ser.read_all().decode(errors='ignore')
    print(f"CMD: {cmd} -> {reply.strip()}")
    return reply

# ---- LoRa Configuration ----
send_cmd("AT")                          # Check module
send_cmd("AT+MODE=LWOTAA")              # Some modules need LoRa mode setup
send_cmd("AT+FREQ=868000000")           # Frequency 868 MHz
send_cmd("AT+SF=9")                     # Spreading Factor (7 = faster, 12 = longer range)
send_cmd("AT+BW=125")                   # Bandwidth 125 kHz
send_cmd("AT+CR=4/5")                   # Coding rate
send_cmd("AT+POWER=20")                 # Tx Power in dBm (max ~22 for SX1268)

# ---- Send Data ----
while True:
    message = "Hello from LoRa sender!"
    send_cmd(f"AT+SEND={message}")
    time.sleep(5)   # Send every 5 sec
