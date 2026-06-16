# Program: VEGA_FINAL.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code

import cv2
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
import time
import psutil
import csv
import serial
import os

print("Initialising VEGA Rideshare Experiment...")

#UART Transmit
def send_uart(message):
    #Encodes string and sends it over UART with a newline terminator
    if ser:
        try:
            ser.write(f"{message}\n".encode('utf-8'))
            print(f">>> Tx: {message}")
        except Exception as e:
            print(f"Failed to send UART message: {e}")

status_file = "flight_status.txt"
if os.path.exists(status_file):
    with open(status_file, "r") as f:
        if "FLOWN" in f.read():
            print("LOCKDOWN ACTIVE: 'FLOWN' flag detected in flight_status.txt.")
            print("To fly again, delete flight_status.txt or clear its contents.")
            exit()

#Configuration
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (1920, 1080), "format": "BGR888"},
    lores={"size": (640, 480), "format": "YUV420"}
)

picam2.configure(config)
picam2.set_controls({
    "AwbEnable": False, 
    "ColourGains": (1.0, 1.0),
    "AfMode": 0,
    "LensPosition": 0.0
})

picam2.start()
target_fps = 15.0

#Initialise UART
try:
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.1
    )
    print("UART Comms linked to LIFTSv2 on /dev/serial0...")
except Exception as e:
    print(f"WARNING: Failed to open serial port: {e}. Relying on fallback timer.")
    ser = None

#Notify Avionics that VEGA is ready
send_uart("VEGA_STARTED")

print("\n--- VEGA IS ARMED AND ON THE PAD ---")
print("Listening for UART launch trigger or 5-minute fallback...")

padStartTime = time.time()
fallbackLimitDuration = 5 * 60
launchTriggered = False

while not launchTriggered:
    try:
        if ser and ser.in_waiting > 0:
            incoming_data = ser.readline().decode('utf-8', errors='ignore').strip()
            if incoming_data != "":
                print(f"<<< Rx: {incoming_data}")
                
            if "START_VEGA" in incoming_data:
                print("UART LAUNCH COMMAND RECEIVED!")
                send_uart("VEGA_START_ACKNOWLEDGED")
                launchTriggered = True
    except Exception as e:
        print(f"UART Rx Error on Pad: {e}. Disabling UART listen.")
        ser = None

    timeOnPad = time.time() - padStartTime
    if timeOnPad > fallbackLimitDuration:
        print("FALLBACK TIMER EXCEEDED (5 MINS). FORCING LAUNCH OVERRIDE!")
        send_uart("VEGA_FAILSAFE_LAUNCH_OVERRIDE")
        launchTriggered = True
    time.sleep(0.1)

try:
    #Auto-increment file name
    run_id = 1
    while os.path.exists(f"VEGA_{run_id}.mp4"):
        run_id += 1
        
    raw_video_file = f"VEGA_Backup_1080p_{run_id}.h264"
    csv_filename = f"VEGA_Telemetry_{run_id}.csv"
    processed_video_file = f"VEGA_{run_id}.mp4"

    send_uart(f"VEGA_INITIALISING_CAMERAS_RUN_{run_id}")
    picam2.start_recording(H264Encoder(), raw_video_file)
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Time (s)', 'Avg NDVI', 'Dyn Min', 'Dyn Max', 'CPU (%)', 'RAM (%)'])
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = cv2.VideoWriter(processed_video_file, fourcc, target_fps, (640, 480))
    
    #Notify over UART that VEGA has started
    send_uart("VEGA_RECORDING_STARTED")
    
    flightStartTime = time.time()
    maxFlightDuration = 20 * 60
    frameCount = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    smoothMin = None
    smoothMax = None
    lastLoggedSecond = -1
    lastHeartbeat = -1
    flightActive = True

    while flightActive:
        try:
            if ser and ser.in_waiting > 0:
                incoming_data = ser.readline().decode('utf-8', errors='ignore').strip()
                if "STOP_VEGA" in incoming_data:
                    print("\nUART STOP COMMAND RECEIVED! ENDING FLIGHT REC.")
                    send_uart("VEGA_STOP_ACKNOWLEDGED")
                    flightActive = False
                    break
        except Exception as e:
            print(f"UART Rx Error in Flight: {e}. Disabling UART listen.")
            ser = None
                
        elapsedExactTime = time.time() - flightStartTime
        elapsed = int(elapsedExactTime)
        
        #Failsafe where force stop if maximum flight duration is exceeded
        if elapsed > maxFlightDuration:
            print("\nFAILSAFE: MAX FLIGHT DURATION (20 MINS) REACHED. AUTO-STOPPING.")
            send_uart("VEGA_FAILSAFE_TIMEOUT_STOP")
            flightActive = False
            break

        rawyuv = picam2.capture_array("lores")
        frame = cv2.cvtColor(rawyuv, cv2.COLOR_YUV2BGR_I420)
        b, g, r = cv2.split(frame)
        r = r.astype(float)
        b = b.astype(float)

        #Aerial Filter
        denominator = r + b
        validPixels = (denominator > 60) & (r < 240) & (b < 240)
        ndviRaw = np.where(validPixels, (r - b) / (denominator + 1e-5), -1.0)

        #Auto-Calibration
        validNdvi = ndviRaw[validPixels]
        if len(validNdvi) > 1000:
            currentMin = np.percentile(validNdvi, 5)
            currentMax = np.percentile(validNdvi, 95)
            if currentMax <= currentMin:
                currentMax = currentMin + 0.01
        else:
            currentMin, currentMax = -0.30, 0.05

        #Temporal Smoothing
        if smoothMin is None:
            smoothMin = currentMin
            smoothMax = currentMax
        else:
            smoothMin = (0.9 * smoothMin) + (0.1 * currentMin)
            smoothMax = (0.9 * smoothMax) + (0.1 * currentMax)

        #Dynamically scale the data based on the smoothed bounds
        scaledNdvi = (ndviRaw - smoothMin) / (smoothMax - smoothMin) * 255
        analysisLayer = np.clip(scaledNdvi, 0, 255).astype(np.uint8)

        #Apply the Jet Colormap
        visualHeatmap = cv2.applyColorMap(analysisLayer, cv2.COLORMAP_JET)

        #Aerial Masks
        maskHealthy = cv2.inRange(analysisLayer, 45, 140)
        maskNotHealthy = cv2.inRange(analysisLayer, 141, 255)

        #Morphological Smoothing
        maskHealthy = cv2.morphologyEx(maskHealthy, cv2.MORPH_OPEN, kernel)
        maskHealthy = cv2.morphologyEx(maskHealthy, cv2.MORPH_CLOSE, kernel)
        maskNotHealthy = cv2.morphologyEx(maskNotHealthy, cv2.MORPH_OPEN, kernel)
        maskNotHealthy = cv2.morphologyEx(maskNotHealthy, cv2.MORPH_CLOSE, kernel)

        #Not Healthy (Red Topographical Outlines)
        contoursRed, _ = cv2.findContours(maskNotHealthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contoursRed:
            area = cv2.contourArea(count)
            if 2000 < area < 250000:
                cv2.drawContours(visualHeatmap, [count], -1, (0, 0, 255), 2)
                x, y, w, h = cv2.boundingRect(count)
                cv2.putText(visualHeatmap, "Not Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        #Healthy plant (Green Topographical Outlines)
        contours_green, _ = cv2.findContours(maskHealthy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for count in contours_green:
            area = cv2.contourArea(count)
            if 2000 < area < 250000:
                cv2.drawContours(visualHeatmap, [count], -1, (0, 255, 0), 2)
                x, y, w, h = cv2.boundingRect(count)
                cv2.putText(visualHeatmap, "Healthy", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        #HUD
        meanValue = validNdvi.mean() if len(validNdvi) > 0 else 0.0
        cpuUsage = psutil.cpu_percent()
        ramUsage = psutil.virtual_memory().percent
        
        overlay = visualHeatmap.copy()
        cv2.rectangle(overlay, (0, 0), (640, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, visualHeatmap, 0.5, 0, visualHeatmap)
        
        cv2.putText(visualHeatmap, f"VEGA Rideshare | T+{elapsed}s | Avg NDVI: {meanValue:.4f}", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(visualHeatmap, f"Sys Usage | CPU: {cpuUsage}% | RAM: {ramUsage}%", (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(visualHeatmap, f"Live Cal: [{smoothMin:.3f} to {smoothMax:.3f}]", (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        expected_frames = int(elapsedExactTime * target_fps)
        while frameCount < expected_frames:
            output.write(visualHeatmap)
            frameCount = frameCount + 1
            
        if elapsed > lastLoggedSecond:
            print(f"Flight T+{elapsed}s | Scale: {smoothMin:.3f} to {smoothMax:.3f} | CPU: {cpuUsage}% | RAM: {ramUsage}%")
            csv_writer.writerow([elapsed, round(meanValue, 4), round(smoothMin, 3), round(smoothMax, 3), cpuUsage, ramUsage])
            lastLoggedSecond = elapsed
            
        #Send status to LIFTSv2 every 10 seconds
        if elapsed % 10 == 0 and elapsed > lastHeartbeat:
            send_uart(f"VEGA_ACTIVE_T+{elapsed}s")
            lastHeartbeat = elapsed

except Exception as e:
    print(f"\nCRITICAL EXCEPTION CAUGHT: {e}")
    send_uart(f"VEGA_ERROR: {e}")

finally:
    send_uart("VEGA_SAVING_DATA")
    output.release()
    picam2.stop_recording()
    picam2.stop()
    csv_file.close()
    send_uart("VEGA_SAVED_AND_STOPPED")
    
    print(f"VEGA stopped! {processed_video_file} saved with {frameCount} frames!")
    
    with open(status_file, "w") as f:
        f.write("FLOWN")
    print(f"Data saved and lockdown file '{status_file}' written. VEGA Complete!")
    
    #Auto-shutdown failsafe
    send_uart("VEGA_DATA_SECURE_INITIATING_SHUTDOWN")
    time.sleep(1)
    
    if ser:
        ser.close()
        
    print("Initiating OS Halt to protect SD Card")
    os.system("sudo shutdown -h now")