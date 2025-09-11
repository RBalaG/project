import serial
import serial.tools.list_ports
import time

def detect_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.device or "AMA" in port.device or "serial" in port.device:
            return port.device
    raise Exception("No LoRa device found!")

def init_lora(port):
    ser = serial.Serial(port, baudrate=9600, timeout=1)
    return ser

if __name__ == "__main__":
    try:
        port = detect_port()
        ser = init_lora(port)
        print(f"[TX] LoRa connected on {port}")

        while True:
            msg = "Hello from Raspberry Pi LoRa Sender!"
            ser.write((msg + "\n").encode())   # send as plain text
            print(f"[TX] Sent: {msg}")
            time.sleep(3)

    except Exception as e:
        print(f"Error: {e}")
