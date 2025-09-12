import serial
import time
import pynmea2

def init_serial():
    # LoRa module connected to Pi UART GPIO pins
    ser = serial.Serial(
        port="/dev/serial0",  # GPIO UART
        baudrate=9600,        # LoRa default baudrate
        timeout=1
    )
    return ser

def read_gps():
    # GPS connected to LoRa TX/RX
    gps = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
    while True:
        line = gps.readline().decode("utf-8", errors="ignore")
        if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
            try:
                msg = pynmea2.parse(line)
                lat = msg.latitude
                lon = msg.longitude
                return f"Lat:{lat}, Lon:{lon}"
            except:
                continue

def main():
    ser = init_serial()

    while True:
        gps_data = read_gps()
        if gps_data:
            message = f"GPS:{gps_data}\n"
            ser.write(message.encode())
            print(f"Sent: {message}")
        time.sleep(1)

if __name__ == "__main__":
    main()
