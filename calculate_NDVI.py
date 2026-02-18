# Program: calculate_NDVI.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
# Program: calculate_ndvi.py
# Description: Processes blue-filtered NoIR images to extract an NDVI proxy 
#              and generates a grayscale intensity map for thresholding.

import cv2
import numpy as np

def process_ndvi(input_path, output_path):
    print(f"Processing {input_path}...")
    img = cv2.imread(input_path)
    if img is None:
        print(f"Failed to load {input_path}!")
        return

    #Split the channels to blue, green and red
    b, g, r = cv2.split(img)
    r = r.astype(float)
    b = b.astype(float)

    #NDVI_proxy = (Red - Blue) / (Red + Blue)
    numerator = r - b
    denominator = (r + b) + 1e-5
    ndvi = numerator / denominator

    #Normalise the data. 
    ndvi_normalized = ((ndvi + 1) / 2) * 255
    
    #Conversion to 8-bit int
    ndvi_8bit = ndvi_normalized.astype(np.uint8)

    #Save greyscale heatmap
    cv2.imwrite(output_path, ndvi_8bit)
    print(f"Saved output to {output_path}\n")
process_ndvi("blue_filter1.jpg", "ndvi_map1.jpg")
process_ndvi("blue_filter2.jpg", "ndvi_map2.jpg")
process_ndvi("blue_filter3.jpg", "ndvi_map3.jpg")