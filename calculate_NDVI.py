# Program: calculate_NDVI.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
import cv2
import numpy as np

def processNDVI(inputPath, outputPath):
    print(f"Processing: {inputPath}...")
    img = cv2.imread(inputPath)
    if img is None:
        print(f"Failed to load: {inputPath}!")
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
    ndviNormalided = ((ndvi + 1) / 2) * 255
    
    #Conversion to 8-bit int
    ndvi8bit = ndviNormalized.astype(np.uint8)

    #Save greyscale heatmap
    cv2.imwrite(outputpath, ndvi8bit)
    print(f"Saved output to {outputPath}\n")
process_ndvi("blue_filter1.jpg", "ndvi_map1.jpg")
process_ndvi("blue_filter2.jpg", "ndvi_map2.jpg")
process_ndvi("blue_filter3.jpg", "ndvi_map3.jpg")