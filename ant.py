import serial
import time

def main():
    # GPS connected to local UART
    gps = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=1)  # adjust port if different
    
    # LoRa UART (transmitter)
    lora = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)  # adjust to correct port

    while True:
        try:
            line = gps.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("$GPGGA") or line.startswith("$GPRMC"):
                print(f"Sending: {line}")
                lora.write((line + "\n").encode())
        except Exception as e:
            print(f"Error: {e}")
            continue
        time.sleep(1)

if __name__ == "__main__":
    main()
