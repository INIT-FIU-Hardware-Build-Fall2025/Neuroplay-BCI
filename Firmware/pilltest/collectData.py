# Car Game Repo
# Manual data collection script for EEG data from Arduino to CSV file

import serial
import csv
import time
import datetime  

COM_PORT = 'COM6'  # Replace with your Arduino's COM port
BAUD_RATE = 115200  # Must match the Arduino's BAUD_RATE

# Open the serial connection
ser = serial.Serial(COM_PORT, BAUD_RATE)

# Create a CSV file to save the data
with open('EEGdata.csv', 'a', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)

    # Set the maximum duration of the data collection (in seconds)
    max_duration = 300

    start_time = time.time()

    print("Collecting data...")

    while time.time() - start_time < max_duration:
        # Read a line of data from the Arduino (until a newline character)
        data = ser.readline().decode("latin-1").strip()

        # Get the current timestamp
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Split the data into a list of values using the comma as a delimiter
        values = data.split(',')

        if len(values) > 0  and values[0].isdigit():
            # Save the data to the CSV file along with the timestamp
            csvwriter.writerow([current_time, values[0]])

ser.close()
