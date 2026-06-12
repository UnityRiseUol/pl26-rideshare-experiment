# Program: VEGA4.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code

import serial
import threading
import sys

print("LIFTSV2 Simulator")

try:
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=115200,
        timeout=0.1
    )
    print("Simulator linked on /dev/serial0. Awaiting VEGA...")
except Exception as e:
    print(f"Failed to open serial port: {e}")
    sys.exit()

#Background task to constantly listen to VEGA
def listen_to_vega():
    while True:
        try:
            if ser.in_waiting > 0:
                incoming = ser.readline().decode('utf-8', errors='ignore').strip()
                if incoming:
                    print(f"\n[<<< VEGA SAYS]: {incoming}")
                    print("Enter command (START / STOP): ", end="", flush=True)
        except Exception:
            pass

#Start background listener
listener_thread = threading.Thread(target=listen_to_vega, daemon=True)
listener_thread.start()

try:
    while True:
        command = input("Enter command (START / STOP): ").strip().upper()
        
        if command == "START":
            ser.write("START_VEGA\n".encode('utf-8'))
            print("[>>> SENT]: START_VEGA")
        elif command == "STOP":
            ser.write("STOP_VEGA\n".encode('utf-8'))
            print("[>>> SENT]: STOP_VEGA")
        elif command != "":
            print("Unknown command. Type START or STOP.")

except KeyboardInterrupt:
    print("\nSimulator shutting down.")
finally:
    ser.close()