import serial

import time

from sx126x import SX126x



GPS_PORT = "/dev/serial0"

GPS_BAUDRATE = 9600



# Initialize GPS

gps = serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=1)

print("[INFO] GPS initialized")



# Initialize LoRa (SPI)

lora = SX126x()

lora.begin()

print("[INFO] LoRa initialized")



def parse_gps(line):

    """Extract latitude & longitude from GPGGA NMEA sentence"""

    if line.startswith("$GPGGA"):

        parts = line.split(",")

        if len(parts) > 5 and parts[2] and parts[4]:

            lat = float(parts[2][:2]) + float(parts[2][2:]) / 60

            lon = float(parts[4][:3]) + float(parts[4][3:]) / 60

            if parts[3] == "S": lat = -lat

            if parts[5] == "W": lon = -lon

            return lat, lon

    return None



while True:

    line = gps.readline().decode('utf-8', errors='ignore').strip()

    if line:

        cords = parse_gps(line)

        if cords:

            lat, lon = cords

            message = f"LAT:{lat:.6f}, LON:{lon:.6f}"

            print("[GPS]", message)



            # Send via LoRa

            lora.send(message.encode('utf-8'))

            print("[TX] Sent:", message)



    time.sleep(1)
