# Program: VEGA2.py
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
target_res = (800, 600)
process_res = (400, 300) 
target_fps = 15.0

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": target_res, "format": "BGR888"})
picam2.configure(config)
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

csv_file = open('VEGA_Telemetry.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time (s)', 'Avg NDVI', 'Dyn Min', 'Dyn Max', 'CPU (%)', 'RAM (%)'])
print("Telemetry Data Logger Armed (VEGA_Telemetry.csv)...")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output = cv2.VideoWriter("VEGA.mp4", fourcc, target_fps, target_res) 
print(f"Recording Started... Strictly synced to {target_fps} FPS for real-time playback...")

duration = 60 
start_time = time.time()
frame_count = 0

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
smooth_min = None
smooth_max = None
current_min, current_max = -0.30, 0.05

mean_val = 0.0
cpu_usage = psutil.cpu_percent()
ram_usage = psutil.virtual_memory().percent

last_logged_sec = -1
last_calibrated_sec = -1 

try:
    while (time.time() - start_time) < duration:
        frame = picam2.capture_array()
        if frame.shape[2] == 4:
            frame = frame[:, :, :3].copy()
            
        small_frame = cv2.resize(frame, process_res, interpolation=cv2.INTER_LINEAR)
            
        b = small_frame[:, :, 0].astype(float)
        r = small_frame[:, :, 2].astype(float)
        
        #Aerial Filter
        denominator = r + b
        valid_pixels = (denominator > 60) & (r < 240) & (b < 240)

        ndvi_raw = np.where(valid_pixels, (r - b) / (denominator + 1e-5), -1.0)
        
        elapsed_exact = time.time() - start_time
        current_sec = int(elapsed_exact)

        #Clock-based calibration by forceing update every 2 seconds
        if current_sec % 2 == 0 and current_sec != last_calibrated_sec:
            valid_ndvi = ndvi_raw[valid_pixels]
            if len(valid_ndvi) > 1000:
                current_min = np.percentile(valid_ndvi, 5)
                current_max = np.percentile(valid_ndvi, 95)
                mean_val = valid_ndvi.mean()
                if current_max <= current_min:
                    current_max = current_min + 0.01
            else:
                current_min, current_max = -0.30, 0.05
                mean_val = 0.0
            last_calibrated_sec = current_sec
            
        #Temporal Smoothing
        if smooth_min is None:
            smooth_min = current_min
            smooth_max = current_max
        else:
            smooth_min = (0.9 * smooth_min) + (0.1 * current_min)
            smooth_max = (0.9 * smooth_max) + (0.1 * current_max)
            
        #Dynamically scale the data 
        scaled_ndvi = (ndvi_raw - smooth_min) / (smooth_max - smooth_min) * 255
        analysis_layer = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet Colormap
        small_heatmap = cv2.applyColorMap(analysis_layer, cv2.COLORMAP_JET)
        mask_healthy = cv2.inRange(analysis_layer, 45, 140)      
        mask_not_healthy = cv2.inRange(analysis_layer, 141, 255) 
        
        #Morphological Smoothing
        mask_healthy = cv2.morphologyEx(mask_healthy, cv2.MORPH_OPEN, kernel)
        mask_healthy = cv2.morphologyEx(mask_healthy, cv2.MORPH_CLOSE, kernel)
        
        mask_not_healthy = cv2.morphologyEx(mask_not_healthy, cv2.MORPH_OPEN, kernel)
        mask_not_healthy = cv2.morphologyEx(mask_not_healthy, cv2.MORPH_CLOSE, kernel)

        #Not Healthy (Red Topographical Outlines)
        contours_red, _ = cv2.findContours(mask_not_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_red:
            area = cv2.contourArea(count)
            if 800 < area < 60000: 
                cv2.drawContours(small_heatmap, [count], -1, (0, 0, 255), 1)
                x, y, w, h = cv2.boundingRect(count)
                cv2.putText(small_heatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

        #Healthy plant (Green Topographical Outlines)
        contours_green, _ = cv2.findContours(mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if 800 < area < 60000: 
                cv2.drawContours(small_heatmap, [count], -1, (0, 255, 0), 1)
                x, y, w, h = cv2.boundingRect(count)
                cv2.putText(small_heatmap, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)

        #Rescale by stretching the finished heatmap back up to 800x600
        hd_heatmap = cv2.resize(small_heatmap, target_res, interpolation=cv2.INTER_LINEAR)

        #HUD 
        if current_sec % 2 == 0 and current_sec != last_logged_sec: 
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            
        overlay = hd_heatmap.copy()
    
        cv2.rectangle(overlay, (0, 0), (target_res[0], 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, hd_heatmap, 0.5, 0, hd_heatmap)
        
        status_text = f"VEGA Rideshare Experiment | T+{current_sec}s | Avg NDVI: {mean_val:.4f}"
        cv2.putText(hd_heatmap, status_text, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        sys_text = f"Sys Usage | CPU: {cpu_usage}% | RAM: {ram_usage}%"
        cv2.putText(hd_heatmap, sys_text, (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        
        cal_text = f"Live Sensor Calibration: [{smooth_min:.3f} to {smooth_max:.3f}]"
        cv2.putText(hd_heatmap, cal_text, (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        
        expected_frames = int(elapsed_exact * target_fps)
        
        while frame_count < expected_frames:
            output.write(hd_heatmap)
            frame_count = frame_count + 1
        
        if current_sec > last_logged_sec:
            print(f"Recording... T+{current_sec}s | Scale: {smooth_min:.3f} to {smooth_max:.3f} | CPU: {cpu_usage}%")
            csv_writer.writerow([current_sec, round(mean_val, 4), round(smooth_min, 3), round(smooth_max, 3), cpu_usage, ram_usage])
            last_logged_sec = current_sec

except KeyboardInterrupt:
    print("\nRecording aborted by user!")

finally:
    output.release()
    picam2.stop()
    csv_file.close() 
    print(f"VEGA stopped! VEGA.mp4 saved with {frame_count} frames!")
    print("Telemetry saved to VEGA_Telemetry.csv")