import time
import spidev
import RPi.GPIO as GPIO
import serial
import pynmea2

# Pin definitions
PIN_RST  = 17
PIN_BUSY = 22
PIN_DIO1 = 23

# LoRa parameters
FREQ      = 433000000
BW        = 125e3
SF        = 7
CR        = 5  # 4/5
PREAMBLE  = 12
TX_POWER  = 14

# Setup GPIO & SPI
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_RST,  GPIO.OUT)
GPIO.setup(PIN_BUSY, GPIO.IN)
GPIO.setup(PIN_DIO1, GPIO.IN)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 4_000_000

# Reset & basic commands
def reset():
    GPIO.output(PIN_RST, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(PIN_RST, GPIO.HIGH)
    time.sleep(0.01)

def wait_busy():
    while GPIO.input(PIN_BUSY): pass

def write_cmd(cmd, data=[]):
    wait_busy()
    buf = [cmd] + data
    spi.xfer2(buf)

def write_reg(addr, val):
    msb, lsb = (addr >> 8) & 0xFF, addr & 0xFF
    write_cmd(0x0D, [msb, lsb, val])

# LoRa initialization
def init_lora():
    reset()
    write_cmd(0x01, [0x83,0x01,0x01])  # SetStandby
    write_cmd(0x8A, [0x01])            # RegTxModulation: LoRa
    write_cmd(0x8B, [0x01])            # RegRxModulation: LoRa
    # Frequency
    frf = int((FREQ / 32e6) * (1<<25))
    write_cmd(0x86, [(frf >>24)&0xFF, (frf>>16)&0xFF, (frf>>8)&0xFF, frf&0xFF])
    # ModParams
    sf_reg = (SF<<4) | (CR-1)
    bw_reg = {125e3:0, 250e3:1, 500e3:2}[BW]
    write_cmd(0x8C, [bw_reg, sf_reg, 0x01])
    # PacketParams
    pl_h = (PREAMBLE >> 8)&0xFF; pl_l = PREAMBLE &0xFF
    write_cmd(0x8E, [pl_h, pl_l, 0x00, 0x00, 0x00, 0xFF, 0x01, 0x00])
    # Tx params
    write_cmd(0x8F, [0x00, TX_POWER])

# Transmit payload
def send(payload: bytes):
    write_cmd(0x0E, [0x00, len(payload)] + list(payload))  # WriteBuffer
    write_cmd(0x83)  # SetTx
    # wait for Done IRQ
    while not GPIO.input(PIN_DIO1): pass
    write_cmd(0x02, [0xFF, 0xFF, 0xFF])  # Clear all IRQs

# Main loop
if __name__ == "__main__":
    init_lora()
    gps = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    print("Transmitter ready")
    try:
        while True:
            line = gps.readline().decode("utf-8", errors="ignore")
            if line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                lat = f"{msg.latitude:.5f}"
                lon = f"{msg.longitude:.5f}"
                packet = f"{lat},{lon}".encode()
                send(packet)
                print("Sent:", packet)
                time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        spi.close()
