import socket
from picarx import Picarx
import time
from collections import deque

HOST = "0.0.0.0"
PORT = 5000

# Require N same messages in a row before acting
SMOOTHING = 3     

def main():
    px = Picarx()
    px.set_dir_servo_angle(0)
    px.forward(0)

    print("BrainControl Server running...")
    print("Waiting for ML client to connect...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)

        conn, addr = s.accept()
        print(f"Connected by {addr}")

        recent = deque(maxlen=SMOOTHING)

        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    print("Client disconnected → STOP")
                    px.forward(0)
                    break

                msg = data.decode().strip().upper()
                print("Received:", msg)

                recent.append(msg)

                # smoothing - only act if last N are the same 
                if len(recent) == SMOOTHING and len(set(recent)) == 1:
                    command = recent[-1]
                else:
                    print("Waiting for stable command…")
                    continue  # wait for consistency

                print(f"Action Triggered: {command}")

                # -------------------------
                #   FOCUS     → GO
                #   UNFOCUS   → STOP
                #   BLINK     → TURN RIGHT (Maybe)
                # -------------------------

                if command == "FOCUS":
                    print("FOCUSED → GO")
                    px.forward(40)

                elif command == "UNFOCUS":
                    print("UNFOCUSED → STOP")
                    px.forward(0)

                # elif command == "BLINK":
                #     print("BLINK DETECTED → TURN RIGHT!")
                #     # Example turn right motion:
                #     px.set_dir_servo_angle(35)   # turn wheels right
                #     px.forward(30)
                #     time.sleep(0.4)
                #     px.forward(0)
                #     px.set_dir_servo_angle(0)
                #     print("TURN COMPLETE")

                else:
                    print("Unknown → STOP (safety)")
                    px.forward(0)

if __name__ == "__main__":
    main()
