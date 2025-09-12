import serial
import time
import pynmea2
from SX126x import SX126x   # Ensure you have correct SX126x library installed

# Initialize GPS (on /dev/serial0 for Raspberry Pi UART)
gps_port = "/dev/serial0"
gps_baudrate = 9600
gps_serial = serial.Serial(gps_port, gps_baudrate, timeout=1)

# Initialize LoRa (SPI pins via GPIO)
LoRa = SX126x(serial_num = 0, cs = 0, reset = 25, busy = 24, irq = 23, txen = 18, rxen = 19)

LoRa.begin(freq=868000000, bw=125000, sf=7, cr=5, syncWord=0x12, power=14, preamble=8, currentLimit=60.0, implicit=False)

print("GPS + LoRa Sender Started")

while True:
    try:
        line = gps_serial.readline().decode('ascii', errors='replace')
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            msg = pynmea2.parse(line)
            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                lat = msg.latitude
                lon = msg.longitude
                gps_data = f"LAT:{lat:.6f},LON:{lon:.6f}"
                print("Sending:", gps_data)
                LoRa.println(gps_data)
                time.sleep(2)
    except Exception as e:
        print("Error:", e)
        time.sleep(1)
