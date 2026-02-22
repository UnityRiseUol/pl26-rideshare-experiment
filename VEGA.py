# Program: VEGA.py
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
print("Intialising VEGA...")

#Configuration
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.configure(config)
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

#Video codec writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("VEGA.mp4", fourcc, 10.0, (640, 480))
print("Recording started...")

duration = 60
start_time = time.time()
frame_count = 0

try:
    while (time.time() - start_time) < duration:
        frame = picam2.capture_array()
        #Slice padding
        if frame.shape[2] == 4:
            frame = frame[:, :, :3].copy()
            
        b, g, r = cv2.split(frame)
        r = r.astype(float)
        b = b.astype(float)

        denominator = r + b
        #If pixel is dark dirt/shadow (< 60) then force the NDVI to -1.0 so it is completely ignored
        ndvi = np.where(denominator > 60, (r - b) / (denominator + 1e-5), -1.0)
        
        scaledNDVI = (ndvi - (-0.20)) / (0.00 - (-0.20)) * 255
        heatmapData = np.clip(scaledNDVI, 0, 255).astype(np.uint8)

        #Healthy mask
        healthyMask = cv2.inRange(heatmapData, 60, 140)
        
        #Not healthy mask
        notHealthyMask = cv2.inRange(heatmapData, 141, 255)

        #Draw green boxes for healthy plants
        contoursHealthy, _ = cv2.findContours(healthyMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contoursHealthy:
            area = cv2.contourArea(count)
            # Increased noise filter slightly to ignore tiny pebbles
            if area > 150: 
                x, y, width, height = cv2.boundingRect(count)
                if (float(height)/float(width)) < 3.0:
                    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
                    cv2.putText(frame, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        #Draw red boxes for not healthy targets
        contoursNotHealthy, _ = cv2.findContours(notHealthyMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contoursNotHealthy:
            area = cv2.contourArea(count)
            if area > 150:
                x, y, width, height = cv2.boundingRect(count)
                if (float(height)/float(width)) < 3.0:
                    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 255), 2)
                    cv2.putText(frame, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        #Write frame and count
        out.write(frame)
        frame_count += 1
        
        if frame_count % 10 == 0:
            elapsed = int(time.time() - start_time)
            # Filter out the dirt we ignored before calculating the terminal averages
            valid_ndvi = ndvi[ndvi > -1.0]
            if len(valid_ndvi) > 0:
                max_val = valid_ndvi.max()
                mean_val = valid_ndvi.mean()
                print(f"Recording... {elapsed}/{duration}s | Max NDVI: {max_val:.3f} | Avg NDVI: {mean_val:.3f}")

except KeyboardInterrupt:
    print("\nRecording stopped!")

finally:
    out.release()
    picam2.stop()
    print(f"VEGA Stopped! Saved {frame_count} frames to VEGA.mp4")