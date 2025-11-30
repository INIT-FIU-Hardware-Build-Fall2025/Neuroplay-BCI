import socket
from picarx import Picarx
import time

HOST = "0.0.0.0"
PORT = 5000


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

        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    print("Client disconnected → STOP")
                    px.forward(0)
                    break

                msg = data.decode().strip().upper()
                print("Received:", msg)

                if msg == "GO":
                    print("UNFOCUSED → GO")
                    px.forward(40)

                elif msg == "STOP":
                    print("FOCUSED → STOP")
                    px.forward(0)

                else:
                    print("Unknown → STOP (safety)")
                    px.forward(0)

if __name__ == "__main__":
    main()
