import serial
import serial.tools.list_ports
import time

# Auto detect port
def detect_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.device or "AMA" in port.device or "serial" in port.device:
            return port.device
    raise Exception("No LoRa device found!")

# Configure LoRa
def init_lora(port):
    ser = serial.Serial(port, baudrate=9600, timeout=1)
    return ser

if __name__ == "__main__":
    try:
        port = detect_port()
        ser = init_lora(port)
        print(f"[TX] LoRa connected on {port}")

        freq = "868000000"   # SX1268 default working frequency
        ser.write(f"AT+FREQ={freq}\r\n".encode())
        time.sleep(0.2)

        while True:
            msg = "Hello from Raspberry Pi LoRa Sender!"
            ser.write(f"AT+SEND={msg}\r\n".encode())
            print(f"[TX] Sent: {msg}")
            time.sleep(3)

    except Exception as e:
        print(f"Error: {e}")
