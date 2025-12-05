import serial
import time
import numpy as np
import pickle
import socket
from scipy.signal import welch
from tkinter import filedialog
import tkinter as tk
from scipy.integrate import trapezoid

# ---------- Helper Functions ----------
def bandpower(signal, sf, band):
    """Compute the power in a specific frequency band."""
    f, Pxx = welch(signal, sf)
    low, high = band
    freq_mask = (f >= low) & (f <= high)
    return trapezoid(Pxx[freq_mask], f[freq_mask])

def extract_features(segment, fs=256):
    """Extract EEG bandpowers and ratios."""
    bp_delta = bandpower(segment, fs, (1,4))
    bp_theta = bandpower(segment, fs, (4,8))
    bp_alpha = bandpower(segment, fs, (8,13))
    bp_beta  = bandpower(segment, fs, (13,30))
    var = np.var(segment)
    ratio_ab = bp_alpha / (bp_beta + 1e-6)
    ratio_tb = bp_theta / (bp_beta + 1e-6)
    return np.array([bp_delta, bp_theta, bp_alpha, bp_beta, var, ratio_ab, ratio_tb])

# ---------- Load Model and Scaler ----------
# Hide the root Tkinter window
root = tk.Tk()
root.withdraw()

# Ask user to choose the KNN model and scaler files
model_path = filedialog.askopenfilename(title="Select KNN model (.pkl)", filetypes=[("Pickle files", "*.pkl")])
scaler_path = filedialog.askopenfilename(title="Select scaler (.pkl)", filetypes=[("Pickle files", "*.pkl")])

# Load the files
with open(model_path, "rb") as f:
    knn = pickle.load(f)
with open(scaler_path, "rb") as f:
    scaler = pickle.load(f)

print(f"✅ Model loaded from: {model_path}")
print(f"✅ Scaler loaded from: {scaler_path}")

# ---------- Serial Setup ----------
PORT = "COM4"       #EEG Pill COM port
BAUD = 115200
fs = 256
win = 1 * fs
blink_threshold = 0.15   # works with normalized -1 to +1 signals

ser = serial.Serial(PORT, BAUD)
time.sleep(2)
print(f"Connected to {PORT} at {BAUD} baud")

# TCP Connection to PiCar
PI_IP = "172.20.10.2"   # The Pi's IP address
PI_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Connecting to PiCar...")
sock.connect((PI_IP, PI_PORT))
print("Connected to PiCar TCP server!")

# ---------- Live Prediction Loop ----------
buffer = []

try:
    print("\nStarting live EEG stream... press Ctrl+C to stop.\n")
    while True:
        raw = ser.readline().decode(errors='ignore').strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue

        buffer.append(value)

        if len(buffer) >= win:
            seg = np.array(buffer[-win:])
            
            # --- Normalize raw ADC (0–1023) to roughly -1 .. +1 ---
            seg = (seg - 512.0) / 512.0

            # --- Feature extraction ---
            feats = extract_features(seg, fs).reshape(1, -1)
            feats_scaled = scaler.transform(feats)

            # --- Predict mental state ---
            pred = knn.predict(feats_scaled)[0]

            # --- Blink override ---
            # print(f"Amplitude range: {np.min(seg):.3f}  to  {np.max(seg):.3f}")
            amp = np.max(np.abs(seg))  # peak amplitude
            if amp > 0.16:             # tuned threshold
                pred = "blink"
                
            print(f"Predicted: {pred}")
            
            # Send current state to PiCar
            try:
                if pred == "focused":
                    sock.sendall(b"FOCUS\n")
                elif pred == "unfocused":
                    sock.sendall(b"UNFOCUS\n")
                elif pred == "blink":
                    sock.sendall(b"BLINK\n")
            except:
                print("Lost connection to PiCar! Please check")
            
            buffer = buffer[-win:]  # slide window forward

except KeyboardInterrupt:
    print("\nStream stopped.")
    ser.close()