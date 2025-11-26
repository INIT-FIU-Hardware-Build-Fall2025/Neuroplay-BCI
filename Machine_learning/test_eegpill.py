import time
import serial
import serial.tools.list_ports

# ==== CONFIGURE THIS PART ====
PORT = "COM4"    # Change if needed (COM3, COM5, etc.)
BAUD = 115200      # Try 9600 first; if garbage, try 115200
NUM_LINES = 200  # How many lines to read before stopping
# =============================

def list_ports():
    print("=== Available serial ports ===")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
    else:
        for p in ports:
            print(f"  {p.device:6}  -  {p.description}")
    print("================================\n")

def main():
    list_ports()

    print(f"Opening {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"❌ Could not open {PORT}: {e}")
        return

    # Give device time to reset if it's an MCU/dongle
    time.sleep(2)
    print(f"✅ Opened {PORT}. Reading {NUM_LINES} lines...\n")

    for i in range(NUM_LINES):
        try:
            # raw = ser.readline()  # bytes
            # line = raw.decode("utf-8", errors="ignore").strip()
            # print(f"{i:03d}: {repr(line)}")
            line = ser.readline()
            print(f"Raw data: {line}")  # Print the raw byte data
        except Exception as e:
            print(f"{i:03d}: Error reading line: {e}")
        # small delay so console is readable
        time.sleep(0.02)

    ser.close()
    print("\nDone. Closed serial port.")

if __name__ == "__main__":
    main()