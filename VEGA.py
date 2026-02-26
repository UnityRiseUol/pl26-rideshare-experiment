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

print("Initialising VEGA Hybrid Payload...")
print("Combining Heatmap Visualisation with CV Classification...")

#Configuration 
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.configure(config)
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output = cv2.VideoWriter("VEGA.mp4", fourcc, 10.0, (640, 480))
print("Recording Started...")

duration = 60 
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
        
        #Brightness Filter
        denominator = r + b
        # Ignore dark pixels (dirt/shadows) by forcing them to -1.0
        ndvi_raw = np.where(denominator > 60, (r - b) / (denominator + 1e-5), -1.0)
        
        #Scaling NDVI
        scaled_ndvi = (ndvi_raw - (-0.30)) / (0.05 - (-0.30)) * 255
        
        # Clip values to stay within 0-255 and convert to 8-bit integer for image processing
        analysis_layer = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet Colormap to turn the grayscale math into a visual heatmap.
        visual_heatmap = cv2.applyColorMap(analysis_layer, cv2.COLORMAP_JET)
        
        #Threshold
        # 0-50: Background noise/dirt (Ignored)
        # 51-135: "Healthy" (Glossy leaves reflecting blue sky -> Cyan/Light Blue on heatmap)
        # 136-255: "Not Healthy" (Matte dead leaves/wood -> Yellow/Orange on heatmap)
        
        mask_healthy = cv2.inRange(analysis_layer, 51, 135)
        mask_not_healthy = cv2.inRange(analysis_layer, 136, 255)
        
        #Not Healthy
        contours_red, _ = cv2.findContours(mask_not_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_red:
            area = cv2.contourArea(count)
            if area > 200:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(visual_heatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        #Healthy plant
        contours_green, _ = cv2.findContours(mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if area > 200:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(visual_heatmap, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        #Heads Up Display to show live scientific telemetry
        elapsed = int(time.time() - start_time)
        
        # Only calculate the mean for valid data (ignoring the dirt we filtered out)
        valid_ndvi = ndvi_raw[ndvi_raw > -1.0]
        mean_val = valid_ndvi.mean() if len(valid_ndvi) > 0 else 0.0
        
        #Semi-transparent background box for text clarity
        overlay = visual_heatmap.copy()
        cv2.rectangle(overlay, (0, 0), (640, 30), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, visual_heatmap, 0.5, 0, visual_heatmap)
        
        status_text = f"VEGA PAYLOAD | T+{elapsed}s | Avg NDVI: {mean_val:.4f}"
        cv2.putText(visual_heatmap, status_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        #Save frame
        output.write(visual_heatmap)
        frame_count += 1
        
        if frame_count % 20 == 0:
            print(f"Recording... {elapsed}/{duration}s processed.")

except KeyboardInterrupt:
    print("\nRecording aborted by user.")

finally:
    output.release()
    picam2.stop()
    print(f"VEGA stopped! VEGA.mp4 saved with {frame_count} frames.")