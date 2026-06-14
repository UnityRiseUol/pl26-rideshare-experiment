# VEGA: Edge-Computed Computer Vision Real-Time NDVI Rideshare Payload

**VEGA (Vegetation Evaluation from Ground to Air)** is a custom-built, real-time computer vision payload intended for the **PL-26** Launch Vehicle Rocket rideshare experiment, developed for the **Unity Rise University of Liverpool Rocket Team** (2025-26 launch).

> **The Problem:** Monitoring vast amounts of vegetation requires farmers to manually inspect thousands of acres on foot. Attempting to check each and every crop individually is incredibly time-consuming, labor-intensive and highly inefficient.
>
> **The Solution:** VEGA acts as an autonomous "eyes in the sky," mapping topographical vegetation health in real-time during flight. This saves farmers countless hours by allowing them to instantly pinpoint and prioritise only the specific crops that are stressed or becoming unhealthy, completely eliminating the need to visit every field.

---

## Project Context
* **Project Title:** LASER - VEGA: Edge-Computed Computer Vision Real-Time NDVI Rideshare Payload
* **Primary Application:** Suborbital Agricultural Health Assessment (NDVI)
* **Avionics Interface:** LIFTSv2 Flight Computer

## What This Software Does

The VEGA flight software operates autonomously on resource-constrained embedded hardware (Raspberry Pi Zero 2W and modified Raspberry Pi Camera Module 3 No IR) during launch to capture and process real-time environmental telemetry. It provides:

* **Real-Time NDVI Processing:** Calculates the Normalised Difference Vegetation Index dynamically using specific wavelength spectrums from the camera feed.
* **Topographical Contouring:** Utilises custom OpenCV morphological operations to map, isolate and draw bounding boxes around healthy and unhealthy crop zones in real time.
* **Avionics UART Handshaking:** Two-way serial communication with the LIFTSv2 flight computer for launch triggers, active flight heartbeat pings and safe shutdown verifications.
* **Aerospace Failsafes:** Built-in launch pad timeouts (5 mins), maximum flight duration limits (30 mins) and automated OS-level shutdown sequences to prevent thermal overload and SD card corruption.
* **Live Telemetry HUD:** Overlays NDVI averages, dynamic auto-calibration scales, elapsed flight time and system resource usage (CPU and RAM usage) directly onto the processed video feed.

## Runtime Architecture

The software is built in Python and optimised for high-stress, offline aerospace environments:

* **Camera Subsystem:** `picamera2` utilising a hardware-accelerated `H264Encoder` for dual-stream capture (saving raw 1080p video while feeding lo-res YUV420 arrays to the processor).
* **Computer Vision:** `cv2` (OpenCV) and `numpy` for core matrix mathematics, dynamic scaling, applying JET colormaps and real-time contour detection.
* **Serial Communications:** `pyserial` for robust, exception-handled UART polling at 115200 baud.
* **System Diagnostics:** `psutil` to monitor and log real-time CPU and virtual memory utilisation to ensure the hardware doesn't thermally throttle during peak loads.
* **OS Integration:** Native `os` commands to manage lockdown files (`flight_status.txt`) and safely halt the Linux OS kernel post-flight.

## Data Outputs

VEGA generates the following data during flight. These files are retrieved directly from the payload's SD card upon successful rocket recovery:

* **`VEGA.mp4`:** The processed stable 15fps video file featuring the applied NDVI colormap, highlighted topographical health contours and the telemetry HUD.
* **`VEGA_Backup_1080p.h264`:** The raw, unadulterated high-definition flight camera feed.
* **`VEGA_Telemetry.csv`:** Structured flight data logging elapsed time, average NDVI, dynamic min/max calibration bounds and hardware usage per second.
* **`flight_status.txt`:** A software lockdown flag generated immediately after landing to prevent the accidental overwrite of mission data if the payload is re-powered in the field.

## Wireless Data Recovery (Web Interface)

To prevent the need for physical disassembly of the rocket's payload bay in the field, VEGA includes a lightweight, built-in web server for wireless file extraction. Once the payload is safely recovered and powered on in, the recovery team can connect to the Raspberry Pi and launch the recovery server via SSH:

```bash
python3 -m http.server 8080
```
By navigating to `http://<VEGA-IP-ADDRESS>:8080` on any mobile device or laptop, the team can access a simple web directory to instantly download the mission video and CSV telemetry files over the air before leaving the recovery site.

## Repository Structure

```text
pl26-rideshare-experiment/
|- VEGA4.py                  #Main applicaiton
|- flight_status.txt         #Auto-generated post-flight lockdown flag
|- VEGA_Telemetry.csv        #Auto-generated mission data log
|- VEGA.mp4                  #Auto-generated processed flight video
|- VEGA_Backup_1080p.h264    #Auto-generated raw flight video
|- README.md