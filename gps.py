import serial

try:
    gps = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)
    print("[INFO] Connected to GPS. Reading data...")

    while True:
        line = gps.readline().decode('utf-8', errors='replace').strip()
        if line:
            print(line)

except Exception as e:
    print(f"[ERROR] {e}")
