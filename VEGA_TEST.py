# Program: VEGA_TEST.py
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
import psutil
import csv 
from gpiozero import Button, LED, TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

#Hardware Configuration
BUTTON_PIN = 27
GREEN_LED = 22
RED_LED = 23
BUZZER_PIN = 24

button = Button(BUTTON_PIN, pull_up=True) 
green = LED(GREEN_LED)
red = LED(RED_LED)
buzzer = TonalBuzzer(BUZZER_PIN)

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
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
smooth_min = None
smooth_max = None
error_occurred = False

try:
    #Start flashing green led while recording
    green.blink(on_time=0.5, off_time=0.5)
    
    while (time.time() - start_time) < duration:
        
        if button.is_pressed:
            print("\nPhysical stop button pressed! Gracefully ending recording...")
            break
            
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
        
        #Auto-Calibration
        valid_ndvi = ndvi_raw[valid_pixels]
        
        if len(valid_ndvi) > 1000:
            current_min = np.percentile(valid_ndvi, 5)
            current_max = np.percentile(valid_ndvi, 95)
            if current_max <= current_min:
                current_max = current_min + 0.01
        else:
            current_min, current_max = -0.30, 0.05
            
        #Temporal Smoothing
        if smooth_min is None:
            smooth_min = current_min
            smooth_max = current_max
        else:
            #Glide smoothly between frame 90% previous data + 10% new data
            smooth_min = (0.9 * smooth_min) + (0.1 * current_min)
            smooth_max = (0.9 * smooth_max) + (0.1 * current_max)
            
        #Dynamically scale the data based on the smoothed bounds
        scaled_ndvi = (ndvi_raw - smooth_min) / (smooth_max - smooth_min) * 255
        analysis_layer = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet Colormap
        visual_heatmap = cv2.applyColorMap(analysis_layer, cv2.COLORMAP_JET)

        #Aerial Masks
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
            if 2000 < area < 250000: 
                cv2.drawContours(visual_heatmap, [count], -1, (0, 0, 255), 2)
                x, y, w, h = cv2.boundingRect(count)
                cv2.putText(visual_heatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        #Healthy plant (Green Topographical Outlines)
        contours_green, _ = cv2.findContours(mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if 2000 < area < 250000:
                cv2.drawContours(visual_heatmap, [count], -1, (0, 255, 0), 2)
                x, y, w, h = cv2.boundingRect(count)
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
        
        cal_text = f"Live Sensor Calibration: [{smooth_min:.3f} to {smooth_max:.3f}]"
        cv2.putText(visual_heatmap, cal_text, (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        
        elapsed_exact = time.time() - start_time
        expected_frames = int(elapsed_exact * target_fps)
        
        while frame_count < expected_frames:
            output.write(visual_heatmap)
            frame_count = frame_count + 1
        
        if frame_count % 15 == 0: 
            print(f"Recording... T+{int(elapsed_exact)}s | Scale: {smooth_min:.3f} to {smooth_max:.3f}")
            csv_writer.writerow([int(elapsed_exact), round(mean_val, 4), round(smooth_min, 3), round(smooth_max, 3), cpu_usage, ram_usage])

except KeyboardInterrupt:
    print("\nRecording stopped by user (Ctrl+C)!")
    
except Exception as e:
    print(f"\nError Occured: {e}")
    error_occurred = True

finally:
    output.release()
    picam2.stop()
    csv_file.close() 
    print(f"VEGA stopped! VEGA.mp4 saved with {frame_count} frames!")
    print("Telemetry saved to VEGA_Telemetry.csv")
    green.off()
    red.off()
    buzzer.stop()
    
    if error_occurred:
        red.on()
        buzzer.play(Tone("A4"))
        sleep(3)
        red.off()
        buzzer.stop()
    else:
        green.on()
        buzzer.play(Tone("C5"))
        sleep(3)
        green.off()
        buzzer.stop()