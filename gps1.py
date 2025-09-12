import serial
import pynmea2

# Serial port (check with ls /dev/serial* or /dev/ttyAMA0 /dev/serial0)
port = "/dev/serial0"
baudrate = 9600

def read_gps():
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            while True:
                data = ser.readline().decode('ascii', errors='replace')
                if data.startswith('$GPGGA') or data.startswith('$GPRMC'):
                    msg = pynmea2.parse(data)
                    print(f"Timestamp: {msg.timestamp}")
                    print(f"Latitude: {msg.latitude} {msg.lat_dir}")
                    print(f"Longitude: {msg.longitude} {msg.lon_dir}")
                    print(f"Altitude: {getattr(msg,'altitude','N/A')}")
                    print("-" * 30)
    except serial.SerialException as e:
        print(f"Error: {e}")
    except pynmea2.ParseError as e:
        print(f"Parse error: {e}")

if __name__ == "__main__":
    read_gps()
