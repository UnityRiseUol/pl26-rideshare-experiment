import serial
import time

try:
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    print("Listening on /dev/serial0 at 115200 baud...")

except Exception as e:
    print(f"Failed to open serial port: {e}")
    exit()

try:
    while True:
        if ser.in_waiting > 0:
            incoming_data = ser.readline().decode('utf-8').rstrip()
            print(f"Received: {incoming_data}")

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    ser.close()