import serial
import time
from sx126x import SX126x

# Configure LoRa (adjust pins as per your wiring)
lora = SX126x(
    serial_num="/dev/ttyS0",
    freq=868,
    addr=0x01,
    power=22,
    rssi=True,
    air_speed=2400,
    relay=False,
    crypt=False
)

# GPS Serial port (change if needed)
gps_serial = serial.Serial('/dev/serial0', 9600, timeout=1)

def get_gps_line():
    while True:
        line = gps_serial.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
            return line.strip()

def main():
    print("Starting GPS to LoRa sender...")
    while True:
        gps_data = get_gps_line()
        print(f"Sending: {gps_data}")
        lora.send(gps_data)
        time.sleep(1)

if __name__ == "__main__":
    main()
