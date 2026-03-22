# Program: VEGA.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import psutil
import csv 

print("Initialising VEGA Rideshare Experiment...")

#Configuration 
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.configure(config)
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()
target_fps = 15.0

csv_file = open('VEGA_Telemetry.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time (s)', 'Avg NDVI', 'Dyn Min', 'Dyn Max', 'CPU (%)', 'RAM (%)'])
print("Telemetry Data Logger Armed (VEGA_Telemetry.csv)...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output = cv2.VideoWriter("VEGA.mp4", fourcc, target_fps, (640, 480))
print(f"Recording Started... Strictly synced to {target_fps} FPS for real-time playback...")

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
        
        #Aerial Filter
        denominator = r + b
        valid_pixels = (denominator > 60) & (r < 240) & (b < 240)
        ndvi_raw = np.where(valid_pixels, (r - b) / (denominator + 1e-5), -1.0)
        
        #Auto-Calibration Engine
        valid_ndvi = ndvi_raw[valid_pixels]
        
        if len(valid_ndvi) > 1000:
            dynamic_min = np.percentile(valid_ndvi, 5)
            dynamic_max = np.percentile(valid_ndvi, 95)
            if dynamic_max <= dynamic_min:
                dynamic_max = dynamic_min + 0.01
        else:
            dynamic_min, dynamic_max = -0.30, 0.05
            
        #Dynamically scale the data based on the live environment bounds
        scaled_ndvi = (ndvi_raw - dynamic_min) / (dynamic_max - dynamic_min) * 255
        analysis_layer = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet Colormap
        visual_heatmap = cv2.applyColorMap(analysis_layer, cv2.COLORMAP_JET)

        #Macro Area Masks
        #Based on visual flight data: Grass = Cyan/Green. Mud/Cars = Orange/Red.
        mask_healthy = cv2.inRange(analysis_layer, 30, 140)
        mask_not_healthy = cv2.inRange(analysis_layer, 141, 255) 
        
        #Not Healthy (Red Boxes - targeting Mud and Cars)
        contours_red, _ = cv2.findContours(mask_not_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_red:
            area = cv2.contourArea(count)
            if 100 < area < 250000:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(visual_heatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        #Healthy plant (Green Boxes - targeting the massive lawn)
        contours_green, _ = cv2.findContours(mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if 100 < area < 250000:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(visual_heatmap, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        #HUD
        elapsed = int(time.time() - start_time)
        mean_val = valid_ndvi.mean() if len(valid_ndvi) > 0 else 0.0
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        overlay = visual_heatmap.copy()
    
        cv2.rectangle(overlay, (0, 0), (640, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, visual_heatmap, 0.5, 0, visual_heatmap)
        
        status_text = f"VEGA Rideshare Experiment | T+{elapsed}s | Avg NDVI: {mean_val:.4f}"
        cv2.putText(visual_heatmap, status_text, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        sys_text = f"Sys Usage | CPU: {cpu_usage}% | RAM: {ram_usage}%"
        cv2.putText(visual_heatmap, sys_text, (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        
        cal_text = f"Live Sensor Calibration: [{dynamic_min:.3f} to {dynamic_max:.3f}]"
        cv2.putText(visual_heatmap, cal_text, (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        
        #Real-Time Frame Sync
        elapsed_exact = time.time() - start_time
        expected_frames = int(elapsed_exact * target_fps)
        
        while frame_count < expected_frames:
            output.write(visual_heatmap)
            frame_count = frame_count + 1
        
        if frame_count % 15 == 0: 
            print(f"Recording... T+{int(elapsed_exact)}s | Scale: {dynamic_min:.3f} to {dynamic_max:.3f}")
            csv_writer.writerow([int(elapsed_exact), round(mean_val, 4), round(dynamic_min, 3), round(dynamic_max, 3), cpu_usage, ram_usage])

except KeyboardInterrupt:
    print("\nRecording aborted by user!")

finally:
    output.release()
    picam2.stop()
    csv_file.close() 
    print(f"VEGA stopped! VEGA.mp4 saved with {frame_count} frames!")
    print("Telemetry saved to VEGA_Telemetry.csv")