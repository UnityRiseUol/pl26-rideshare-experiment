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

print("Initialising VEGA Auto-Calibrating Aerial Payload...")

#Configuration 
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
picam2.configure(config)
picam2.set_controls({"AwbEnable": False, "ColourGains": (1.0, 1.0)})
picam2.start()

target_fps = 15.0

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
output = cv2.VideoWriter("VEGA_Flight.mp4", fourcc, target_fps, (640, 480))
print(f"Recording Started at strictly synced {target_fps} FPS...")

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
        
        #Auto-Callibration Enginer to callibrate in real-time surroundings of threshold
        valid_ndvi = ndvi_raw[valid_pixels]
        
        if len(valid_ndvi) > 1000:
            #Find 5th and 95th percentiles to determine the true environmental limits (ignoring random noise)
            dynamic_min = np.percentile(valid_ndvi, 5)
            dynamic_max = np.percentile(valid_ndvi, 95)
            
            #Stop division by zero
            if dynamic_max <= dynamic_min:
                dynamic_max = dynamic_min + 0.01
        else:
            # Fallback failsafe if the camera gets covered
            dynamic_min, dynamic_max = -0.30, 0.05
            
        # Dynamically scale the data based on the LIVE environment bounds!
        scaled_ndvi = (ndvi_raw - dynamic_min) / (dynamic_max - dynamic_min) * 255
        analysis_layer = np.clip(scaled_ndvi, 0, 255).astype(np.uint8)
        
        #Apply the Jet Colormap
        visual_heatmap = cv2.applyColorMap(analysis_layer, cv2.COLORMAP_JET)

        #Dynamic thresholds
        #0-19: Absolute bottom noise (Ignored)
        #20-127: "Healthy" (Glossy/moist plants reflecting blue sky -> Lower half of dynamic scale)
        #128-235: "Not Healthy" (Matte/dry dead plants -> Upper half of dynamic scale)
        #236-255: Absolute top noise/urban reflection (Ignored)
        
        mask_healthy = cv2.inRange(analysis_layer, 20, 127)
        mask_not_healthy = cv2.inRange(analysis_layer, 128, 235) 
        
        #Not Healthy (Red Boxes)
        contours_red, _ = cv2.findContours(mask_not_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_red:
            area = cv2.contourArea(count)
            if 100 < area < 10000:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(visual_heatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        #Healthy plant (Green Boxes)
        contours_green, _ = cv2.findContours(mask_healthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if 100 < area < 10000:
                x, y, w, h = cv2.boundingRect(count)
                if (float(h)/float(w)) < 4.0:
                    cv2.rectangle(visual_heatmap, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(visual_heatmap, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        #EXPANDED HUD
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
        
        #Display the live calibration limits in HUD
        cal_text = f"Live Sensor Callibration: [{dynamic_min:.3f} to {dynamic_max:.3f}]"
        cv2.putText(visual_heatmap, cal_text, (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        #Real-time Frame Sync
        elapsed_exact = time.time() - start_time
        expected_frames = int(elapsed_exact * target_fps)
        while frame_count < expected_frames:
            output.write(visual_heatmap)
            frame_count += 1
        
        if frame_count % 30 == 0: 
            print(f"Recording... T+{int(elapsed_exact)}s | Scale: {dynamic_min:.3f} to {dynamic_max:.3f}")

except KeyboardInterrupt:
    print("\nRecording aborted by user!")

finally:
    output.release()
    picam2.stop()
    print(f"VEGA stopped! VEGA_Flight.mp4 saved with {frame_count} frames!")