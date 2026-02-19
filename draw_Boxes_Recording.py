# Program: draw_Boxes_Recording.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
import cv2
import numpy as np
from picamera2 import Picamera2
import time

#Configuration
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

#Video codec writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("video_recording.mp4", fourcc, 10.0, (640, 480))
print("Recording has started...")

duration = 60
start_time = time.time()
frame_count = 0

try:
    while (time.time() - start_time) < duration:
        
        frame = picam2.capture_array()
        #Slice 4th padding channel to get BGR and copy to continuous memory
        if frame.shape[2] == 4:
            frame = frame[:, :, :3].copy()
        b, g, r = cv2.split(frame)
        r = r.astype(float)
        b = b.astype(float)
        ndvi = (r - b) / ((r + b) + 1e-5)
        
        #Normalise to 0-255 range
        ndvi_normalized = ((ndvi + 1) / 2) * 255
        ndvi_8bit = ndvi_normalized.astype(np.uint8)
        
        #Thresholding
        #Set 135 to be baselibe threshold for "alive plant"
        #Above 135 means set to 255 white and thr rest is 0 black.
        _, mask = cv2.threshold(ndvi_8bit, 135, 255, cv2.THRESH_BINARY)
        
        #Contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        #Draw boxes
        for count in contours:
            area = cv2.contourArea(count)
            if area > 100:  # Filter noise for 640x480 resolution
                x, y, w, h = cv2.boundingRect(count)
                aspect_ratio = float(h) / float(w)
                
                #Filter noise
                if aspect_ratio < 3.0:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        out.write(frame)
        frame_count = frame_count + 1
        
        if frame_count % 10 == 0:
            elapsed = int(time.time() - start_time)
            print(f"Recording... {elapsed}/{duration} seconds elapsed.")

except KeyboardInterrupt:
    print("\nRecording aborted by user.")

finally:
    out.release()
    picam2.stop()
    print(f"Payload Shut Down. Saved {frame_count} frames to video_recording.mp4")