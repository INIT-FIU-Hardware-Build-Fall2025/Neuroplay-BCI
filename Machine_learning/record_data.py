import serial
import time
from datetime import datetime

# Setup the serial port (ensure it matches your Arduino setup)
serial_port = "COM4"  # Adjust to your port (e.g., "COM4" for Windows, "/dev/ttyUSB0" for Linux)
baud_rate = 115200    # Make sure this matches the baud rate in your Arduino code

# File to store data
# file_name = "data.txt"

# Create a unique filename for each run
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f"data_{timestamp}.txt"

def open_serial_connection(port, baud_rate):
    """Open the serial connection."""
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        time.sleep(2)  # Allow time for the Arduino to initialize
        print(f"Connected to {port} at {baud_rate} baud.")
        return ser
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return None

def write_data_to_file(data, filename):
    """Write data to a text file."""
    try:
        with open(filename, "a") as file:  # Open file in append mode
            file.write(data + '\n')  # Write data and add a newline
            print(f"Data written to {filename}.")
    except Exception as e:
        print(f"Error writing to file: {e}")

def main():
    # Open serial connection
    ser = open_serial_connection(serial_port, baud_rate)
    if ser is None:
        return

    try:
        while True:
            # Read a line of data from the serial port
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:  # Only write if the line is not empty
                print(f"Received: {line}")  # Print received data (optional)
                write_data_to_file(line, file_name)  # Store the data in the file
            time.sleep(0.1)  # Delay to prevent flooding the file with data

    except KeyboardInterrupt:
        print("Program interrupted. Closing serial connection...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
