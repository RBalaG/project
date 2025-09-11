#!/usr/bin/env python3
import serial
import time
import os
import glob
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoRaCommunicator:
    def __init__(self, frequency=868.0, sf=7, bw=125, cr=5, power=22):
        self.frequency = frequency
        self.sf = sf  # Spreading factor
        self.bw = bw  # Bandwidth
        self.cr = cr  # Coding rate
        self.power = power
        self.ser = None
        self.port = None
        
    def detect_lora_port(self):
        """Automatically detect LoRa hat serial port"""
        possible_ports = []
        
        # Common USB serial ports
        possible_patterns = ['/dev/ttyUSB*', '/dev/ttyAMA*', '/dev/serial0', '/dev/serial1']
        
        for pattern in possible_patterns:
            if '*' in pattern:
                possible_ports.extend(glob.glob(pattern))
            else:
                if os.path.exists(pattern):
                    possible_ports.append(pattern)
        
        # Try each port to find LoRa module
        for port in possible_ports:
            try:
                logger.info(f"Testing port: {port}")
                test_ser = serial.Serial(
                    port=port,
                    baudrate=9600,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=2
                )
                
                # Send AT command to check if it's LoRa module
                test_ser.write(b'AT\r\n')
                time.sleep(0.1)
                response = test_ser.read_all().decode('utf-8', errors='ignore')
                
                if 'OK' in response or '+++' in response:
                    logger.info(f"LoRa module found on port: {port}")
                    test_ser.close()
                    return port
                
                test_ser.close()
                
            except (serial.SerialException, OSError) as e:
                continue
        
        logger.error("No LoRa module detected on any port!")
        return None

    def initialize_lora(self):
        """Initialize LoRa module with proper settings"""
        self.port = self.detect_lora_port()
        
        if not self.port:
            raise Exception("Could not detect LoRa module!")
        
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            
            # Reset module
            self.send_command('AT+RESET')
            time.sleep(2)
            
            # Set mode to LoRa
            self.send_command('AT+MODE=0')
            
            # Set frequency (CRITICAL: Must match on both devices)
            self.send_command(f'AT+CFG={self.frequency}')
            
            # Set spreading factor
            self.send_command(f'AT+SF={self.sf}')
            
            # Set bandwidth
            self.send_command(f'AT+BW={self.bw}')
            
            # Set coding rate
            self.send_command(f'AT+CR={self.cr}')
            
            # Set power
            self.send_command(f'AT+POWER={self.power}')
            
            logger.info("LoRa module initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LoRa: {e}")
            raise

    def send_command(self, command, wait_time=0.1):
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
            # Switch to transmit mode
            self.send_command('AT+MODE=1')
            time.sleep(0.1)
            
            # Send message
            command = f'AT+SEND={message}'
            response = self.send_command(command, wait_time=0.5)
            
            # Return to receive mode
            self.send_command('AT+MODE=0')
            
            if 'OK' in response:
                logger.info(f"Message sent: {message}")
                return True
            else:
                logger.warning(f"Send may have failed. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False

    def receive_message(self, timeout=10):
        """Receive message with timeout"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check for incoming data
                if self.ser.in_waiting > 0:
                    data = self.ser.read_all().decode('utf-8', errors='ignore')
                    
                    if data.strip() and 'RCV' in data:
                        # Extract message from response
                        lines = data.split('\r\n')
                        for line in lines:
                            if 'RCV' in line:
                                parts = line.split(',')
                                if len(parts) >= 2:
                                    message = parts[1].strip()
                                    logger.info(f"Received: {message}")
                                    return message
                
                time.sleep(0.1)
            
            return None
            
        except Exception as e:
            logger.error(f"Receive failed: {e}")
            return None

    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial connection closed")

def main():
    print("LoRa Communicator - Choose mode:")
    print("1. Transmitter")
    print("2. Receiver")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    # IMPORTANT: Same frequency on both devices!
    lora = LoRaCommunicator(frequency=868.0)  # Use 868MHz for EU, 915MHz for US
    
    try:
        lora.initialize_lora()
        
        if choice == '1':
            print("Transmitter mode activated. Type 'quit' to exit.")
            while True:
                message = input("Enter message to send: ")
                if message.lower() == 'quit':
                    break
                lora.send_message(message)
                time.sleep(1)  # Short delay between messages
        
        elif choice == '2':
            print("Receiver mode activated. Press Ctrl+C to exit.")
            print("Waiting for messages...")
            while True:
                message = lora.receive_message(timeout=5)
                if message:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: {message}")
                time.sleep(0.1)
        
        else:
            print("Invalid choice!")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        lora.close()

if __name__ == "__main__":
    main()
