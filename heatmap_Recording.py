# Program: heatmap_Recording.py
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

print("Initializing Telemetry and Heatmap Payload...")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.configure(config)

picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("calibrated_flight_data.mp4", fourcc, 10.0, (640, 480))
print("Recording Calibrated Heatmap Video...")

duration = 30
start_time = time.time()
frame_count = 0

try:
    while (time.time() - start_time) < duration:
        frame = picam2.capture_array()
        
        if frame.shape[2] == 4:
            frame = frame[:, :, :3].copy()
            
        b, g, r = cv2.split(frame)
        r = r.astype(float)
        b = b.astype(float)
        
        #Calculate raw NDVI
        ndvi = (r - b) / ((r + b) + 1e-5)
        scaled_ndvi = (ndvi - (-0.20)) / (0.00 - (-0.20)) * 255
        
        #Clip to ensure no math errors, and convert to 8-bit image format
        heatmap_data = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet colourmap heatmap
        heatmap = cv2.applyColorMap(heatmap_data, cv2.COLORMAP_JET)
        
        out.write(heatmap)
        frame_count = frame_count + 1
        
        if frame_count % 10 == 0:
            elapsed = int(time.time() - start_time)
            min_val = ndvi.min()
            max_val = ndvi.max()
            mean_val = ndvi.mean()
            print(f"Time: {elapsed}s | NDVI -> Min: {min_val:.3f}, Max: {max_val:.3f}, Avg: {mean_val:.3f}")

except KeyboardInterrupt:
    print("\nRecording aborted by user.")

finally:
    out.release()
    picam2.stop()
    print(f"Payload Shut Down. Saved {frame_count} frames to calibrated_flight_data.mp4")