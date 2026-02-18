# Program: camera_Test.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
from picamera2 import Picamera2
import time

picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (1920, 1080)})
picam2.configure(config)
picam2.start()
time.sleep(2)
picam2.capture_file("blue_filter3.jpg")
picam2.stop()

print("Image captured successfully")
