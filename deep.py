#!/usr/bin/env python3
import serial
import serial.tools.list_ports
import time
import os
import glob
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoRaCommunicator:
    def __init__(self, frequency=868.0, sf=7, bw=125, cr=5, power=22, baudrate=9600):
        self.frequency = frequency
        self.sf = sf
        self.bw = bw
        self.cr = cr
        self.power = power
        self.baudrate = baudrate
        self.ser = None
        self.port = None
        
    def detect_lora_port(self):
        """Enhanced port detection with detailed debugging"""
        logger.info("Starting port detection...")
        
        # List all available serial ports
        ports = serial.tools.list_ports.comports()
        logger.info(f"Available ports: {[p.device for p in ports]}")
        
        # Common ports to check (in order of priority)
        port_priority = [
            '/dev/ttyAMA0',    # GPIO serial
            '/dev/serial0',    # Alias for GPIO serial
            '/dev/ttyUSB0',    # USB serial
            '/dev/ttyUSB1',
            '/dev/ttyACM0',    # ACM devices
            '/dev/ttyACM1'
        ]
        
        # Add all detected ports to the list
        for port in ports:
            if port.device not in port_priority:
                port_priority.append(port.device)
        
        logger.info(f"Testing ports in order: {port_priority}")
        
        for port in port_priority:
            if not os.path.exists(port):
                logger.debug(f"Port {port} does not exist, skipping")
                continue
                
            logger.info(f"Testing port: {port}")
            
            try:
                # Try with different baudrates
                for baud in [9600, 115200, 57600, 38400, 19200]:
                    try:
                        logger.debug(f"Trying baudrate: {baud}")
                        test_ser = serial.Serial(
                            port=port,
                            baudrate=baud,
                            bytesize=8,
                            parity='N',
                            stopbits=1,
                            timeout=1,
                            write_timeout=1
                        )
                        
                        # Clear buffer
                        test_ser.reset_input_buffer()
                        test_ser.reset_output_buffer()
                        
                        # Try different AT commands
                        test_commands = [b'AT\r\n', b'AT+\r\n', b'+++', b'AT\n']
                        
                        for cmd in test_commands:
                            try:
                                test_ser.write(cmd)
                                time.sleep(0.5)
                                response = test_ser.read_all().decode('utf-8', errors='ignore')
                                logger.debug(f"Command: {cmd}, Response: {repr(response)}")
                                
                                if any(x in response.upper() for x in ['OK', 'AT', 'READY', '+++']):
                                    logger.info(f"✅ LoRa module detected on {port} with baudrate {baud}")
                                    test_ser.close()
                                    self.baudrate = baud
                                    return port
                                    
                            except Exception as e:
                                logger.debug(f"Command {cmd} failed: {e}")
                                continue
                        
                        test_ser.close()
                        
                    except serial.SerialException as e:
                        logger.debug(f"Baudrate {baud} failed: {e}")
                        continue
                    except Exception as e:
                        logger.debug(f"Unexpected error: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Port {port} test failed: {e}")
                continue
        
        logger.error("❌ No LoRa module detected on any port!")
        return None

    def initialize_lora(self):
        """Initialize LoRa module"""
        self.port = self.detect_lora_port()
        
        if not self.port:
            raise Exception("Could not detect LoRa module! Check connections and try again.")
        
        try:
            logger.info(f"Initializing LoRa on {self.port} with baudrate {self.baudrate}")
            
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1,
                write_timeout=1
            )
            
            # Give module time to initialize
            time.sleep(2)
            
            # Clear buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # Test connection
            response = self.send_command('AT', wait_time=0.5)
            logger.debug(f"AT response: {repr(response)}")
            
            if 'OK' not in response:
                logger.warning("AT command didn't return OK, but continuing...")
            
            # Reset to default
            self.send_command('AT+RESET')
            time.sleep(2)
            
            # Basic configuration
            self.send_command('AT+MODE=0')          # LoRa mode
            self.send_command(f'AT+CFG={self.frequency}')
            self.send_command(f'AT+SF={self.sf}')
            self.send_command(f'AT+BW={self.bw}')
            self.send_command(f'AT+CR={self.cr}')
            self.send_command(f'AT+POWER={self.power}')
            
            logger.info("✅ LoRa module initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LoRa: {e}")
            if self.ser:
                self.ser.close()
            raise

    def send_command(self, command, wait_time=0.5):
        """Send AT command to LoRa module"""
        try:
            self.ser.write((command + '\r\n').encode())
            time.sleep(wait_time)
            response = self.ser.read_all().decode('utf-8', errors='ignore')
            return response.strip()
        except Exception as e:
            logger.error(f"Command failed: {command}, Error: {e}")
            return ""

    def send_message(self, message):
        """Send message via LoRa"""
        try:
            logger.debug(f"Preparing to send: {message}")
            
            # Switch to transmit mode
            self.send_command('AT+MODE=1')
            time.sleep(0.1)
            
            # Send message
            command = f'AT+SEND={message}'
            response = self.send_command(command, wait_time=1)
            logger.debug(f"Send response: {repr(response)}")
            
            # Return to receive mode
            self.send_command('AT+MODE=0')
            
            if 'OK' in response:
                logger.info(f"✅ Message sent: {message}")
                return True
            else:
                logger.warning(f"⚠️ Send may have failed. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Send failed: {e}")
            return False

    def receive_message(self, timeout=10):
        """Receive message with timeout"""
        try:
            start_time = time.time()
            logger.debug("Listening for messages...")
            
            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    data = self.ser.read_all().decode('utf-8', errors='ignore')
                    logger.debug(f"Raw received: {repr(data)}")
                    
                    if data.strip():
                        # Look for RCV pattern or any meaningful data
                        lines = data.split('\r\n')
                        for line in lines:
                            line = line.strip()
                            if line and ('RCV' in line or len(line) > 3):
                                logger.info(f"📨 Received data: {line}")
                                return line
                
                time.sleep(0.1)
            
            logger.debug("Receive timeout")
            return None
            
        except Exception as e:
            logger.error(f"Receive failed: {e}")
            return None

    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial connection closed")

def test_ports():
    """Test function to check all available ports"""
    print("🔍 Testing all available serial ports...")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("❌ No serial ports found!")
        return
    
    print(f"Found {len(ports)} ports:")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")

def main():
    print("=" * 50)
    print("LoRa SX1268 Communicator")
    print("=" * 50)
    
    # First test available ports
    test_ports()
    print()
    
    print("Choose mode:")
    print("1. Transmitter")
    print("2. Receiver")
    print("3. Port test only")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == '3':
        return
    
    # Initialize LoRa
    lora = LoRaCommunicator(frequency=868.0)  # Change to 915.0 if in US
    
    try:
        lora.initialize_lora()
        
        if choice == '1':
            print("📡 Transmitter mode activated. Type 'quit' to exit.")
            while True:
                message = input("Enter message to send: ")
                if message.lower() == 'quit':
                    break
                success = lora.send_message(message)
                if not success:
                    print("Send failed, check connection")
                time.sleep(1)
        
        elif choice == '2':
            print("📻 Receiver mode activated. Press Ctrl+C to exit.")
            print("Waiting for messages...")
            while True:
                message = lora.receive_message(timeout=5)
                if message:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📨 {message}")
                time.sleep(0.1)
        
        else:
            print("Invalid choice!")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check:")
        print("1. LoRa hat is properly connected")
        print("2. Correct frequency setting (868MHz EU/915MHz US)")
        print("3. Power supply is adequate")
        print("4. Antenna is connected")
    finally:
        lora.close()

if __name__ == "__main__":
    main()
