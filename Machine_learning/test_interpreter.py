import os
import time
import threading
from collections import deque

import numpy as np
import joblib
import serial
from scipy.signal import welch

import tkinter as tk
from tkinter import ttk

# ==========================
# 1) CONFIG
# ==========================

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH    = os.path.join(BASE_DIR, "best_calibrated_rf_model (1).joblib")

SERIAL_PORT   = "COM4"   # <- CHANGE ME to your EEG serial port
BAUD_RATE     = 115200   # <- CHANGE ME to match your device
SF            = 10      # sampling frequency (Hz)
WINDOW_SEC    = 2.0      # window length in seconds
WINDOW_SAMPLES = int(SF * WINDOW_SEC)

SMOOTH_WINDOW = 5        # how many recent predictions to majority-vote
READ_DELAY    = 0.004    # ~250 samples/sec ≈ 4 ms per sample (tweak if needed)

# ==========================
# 2) LOAD MODEL
# ==========================

# best_calibrated_rf_model.joblib should be your Calibrated RF from training
model = joblib.load(MODEL_PATH)

# model should support .predict_proba on a (1, 15) feature vector

# ==========================
# 3) FEATURE EXTRACTION
# ==========================

def bandpower(data, sf, band):
    """Compute band power in a given frequency band using Welch + trapezoid integration."""
    f, Pxx = welch(data, sf)
    low, high = band
    mask = (f >= low) & (f <= high)
    if not np.any(mask):
        return 0.0
    return np.trapezoid(Pxx[mask], f[mask])

def extract_features_from_segment(seg, sf):
    """
    Given a 1D EEG segment and sampling freq, compute a 15-dim feature vector:
      - raw bandpowers: delta, theta, alpha, beta
      - band ratios: theta/alpha, alpha/beta, theta/beta
      - normalized bandpowers: each band / total power
      - log bandpowers
    Returns: (15,) numpy array of floats.
    """
    seg = np.asarray(seg, dtype=float)

    # Basic bandpowers
    delta = bandpower(seg, sf, (1, 4))
    theta = bandpower(seg, sf, (4, 8))
    alpha = bandpower(seg, sf, (8, 13))
    beta  = bandpower(seg, sf, (13, 30))

    total = delta + theta + alpha + beta + 1e-8  # avoid divide-by-zero
    eps = 1e-8

    # Ratios
    theta_alpha = theta / (alpha + eps)
    alpha_beta  = alpha / (beta  + eps)
    theta_beta  = theta / (beta  + eps)

    # Normalized powers
    delta_norm = delta / total
    theta_norm = theta / total
    alpha_norm = alpha / total
    beta_norm  = beta  / total

    # Log powers
    log_delta = np.log(delta + eps)
    log_theta = np.log(theta + eps)
    log_alpha = np.log(alpha + eps)
    log_beta  = np.log(beta  + eps)

    features = [
        delta, theta, alpha, beta,
        theta_alpha, alpha_beta, theta_beta,
        delta_norm, theta_norm, alpha_norm, beta_norm,
        log_delta, log_theta, log_alpha, log_beta,
    ]
    return np.array(features, dtype=float)

def predict_focus(features_vec):
    """
    features_vec: 1D array of shape (15,)
    Returns: (label, confidence) where label is 'focused' or 'unfocused',
             confidence is max probability in [0,1].
    """
    x = np.asarray(features_vec, dtype=float).reshape(1, -1)
    probs = model.predict_proba(x)[0]  # shape (2,)
    classes = model.classes_
    idx_max = np.argmax(probs)
    label = classes[idx_max]
    conf  = float(probs[idx_max])
    return label, conf

# ==========================
# 4) SERIAL SETUP
# ==========================

def open_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # allow device to reset
        return ser
    except Exception as e:
        print(f"Could not open serial port {SERIAL_PORT}: {e}")
        return None

ser = open_serial()

# ==========================
# 5) TKINTER GUI
# ==========================

root = tk.Tk()
root.title("EEG Focus Monitor")
root.geometry("500x250")

# Simple light theme
root.configure(bg="#222222")
style = ttk.Style()
style.theme_use("default")
style.configure("TFrame", background="#222222")
style.configure("TLabel", background="#222222", foreground="white", font=("Arial", 12))
style.configure("Title.TLabel", font=("Arial", 18, "bold"))
style.configure("State.TLabel", font=("Arial", 24, "bold"))

main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill="both", expand=True)

title_lbl = ttk.Label(main_frame, text="EEG Focus Monitor", style="Title.TLabel")
title_lbl.pack(pady=(0, 20))

# Current state label
state_var = tk.StringVar(value="--")
state_lbl = ttk.Label(main_frame, textvariable=state_var, style="State.TLabel")
state_lbl.pack(pady=(0, 10))

# Confidence progress bar + label
conf_frame = ttk.Frame(main_frame)
conf_frame.pack(pady=(10, 0), fill="x")

conf_var = tk.DoubleVar(value=0.0)
conf_bar = ttk.Progressbar(conf_frame, variable=conf_var, maximum=100, length=300)
conf_bar.pack(side="left", padx=(0, 10))

conf_text_var = tk.StringVar(value="0.0%")
conf_lbl = ttk.Label(conf_frame, textvariable=conf_text_var)
conf_lbl.pack(side="left")

# Start/Stop buttons
btn_frame = ttk.Frame(main_frame)
btn_frame.pack(pady=20)

start_btn = ttk.Button(btn_frame, text="Start")
stop_btn  = ttk.Button(btn_frame, text="Stop")
start_btn.pack(side="left", padx=10)
stop_btn.pack(side="left", padx=10)
stop_btn.state(["disabled"])

# ==========================
# 6) REALTIME LOOP
# ==========================

running = False
sample_buffer = deque(maxlen=WINDOW_SAMPLES)  # holds last 2s of samples
pred_window   = deque(maxlen=SMOOTH_WINDOW)   # for majority-vote smoothing

def smooth_label(new_label):
    """Majority vote over last SMOOTH_WINDOW predictions."""
    pred_window.append(new_label)
    labels, counts = np.unique(list(pred_window), return_counts=True)
    return labels[np.argmax(counts)]

def update_gui(label, conf):
    """Safe-ish GUI update from the worker."""
    # Make label more friendly
    label_str = label.upper()
    state_var.set(label_str)

    # Color code by state
    if label.lower() == "focused":
        state_lbl.configure(foreground="#4CAF50")  # green
    elif label.lower() == "unfocused":
        state_lbl.configure(foreground="#F44336")  # red
    else:
        state_lbl.configure(foreground="white")

    conf_pct = conf * 100.0
    conf_var.set(conf_pct)
    conf_text_var.set(f"{conf_pct:.1f}%")

def read_loop():
    global running, ser
    sample_buffer.clear()
    pred_window.clear()

    if ser is None:
        print("No serial connection. Cannot start.")
        return

    print("Starting read_loop... waiting for data from", SERIAL_PORT)

    while running:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            # Debug: print a few raw lines at the start
            # (you can comment this out later)
            # print("RAW:", repr(line))

            # Expect format like: "133,-0.001280" or "133, -0.001280"
            # or maybe "133 -0.001280"
            # We'll be flexible: replace commas with spaces and split.
            parts = line.replace(",", " ").split()

            if len(parts) < 2:
                # Not enough pieces, skip this line
                continue

            # Counter is parts[0], EEG value is parts[1]
            try:
                val = float(parts[1])
            except ValueError:
                # Could not parse EEG value, skip
                continue

            # Add EEG sample to sliding buffer
            sample_buffer.append(val)

            # Only predict once we have a full 2s window
            if len(sample_buffer) == WINDOW_SAMPLES:
                seg = np.array(sample_buffer, dtype=float)
                feats = extract_features_from_segment(seg, SF)
                label, conf = predict_focus(feats)

                # Smooth label over last few predictions
                smoothed_label = smooth_label(label)

                # Update GUI safely from this thread
                root.after(0, update_gui, smoothed_label, conf)

            time.sleep(READ_DELAY)

        except Exception as e:
            print("Error in read_loop:", e)
            time.sleep(0.1)


def start_reading():
    global running, ser
    if running:
        return
    if ser is None:
        ser_local = open_serial()
        if ser_local is None:
            print("Cannot start: serial port unavailable.")
            return
        else:
            ser = ser_local

    running = True
    start_btn.state(["disabled"])
    stop_btn.state(["!disabled"])
    th = threading.Thread(target=read_loop, daemon=True)
    th.start()

def stop_reading():
    global running
    running = False
    start_btn.state(["!disabled"])
    stop_btn.state(["disabled"])

start_btn.config(command=start_reading)
stop_btn.config(command=stop_reading)

# ==========================
# 7) RUN APP
# ==========================

root.mainloop()
