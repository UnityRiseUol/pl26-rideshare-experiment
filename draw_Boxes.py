# Program: draw_Boxes.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
import cv2
import numpy as np
def detectPlants(originalImagePath, NDVIMapPath, OutputPath):
    print(f"Processing boxes for: {originalImagePath}...")
    
    #Load original colour image and greyscale NDVI image
    img = cv2.imread(originalImagePath)
    NDVIMap = cv2.imread(NDVIMapPath, cv2.IMREAD_GRAYSCALE)

    if img is None or NDVIMap is None:
        return
    totalArea = img.shape[0] * img.shape[1]
    
    #Thresholding
    #Set 140 to be baselibe threshold for "alive plant"
    #Above 140 means set to 255 white and thr rest is 0 black
    _, mask = cv2.threshold(NDVIMap, 120, 255, cv2.THRESH_BINARY)
    mask_output_path = OutputPath.replace(".jpg", "_mask.jpg")
    cv2.imwrite(mask_output_path, mask)

    # Find Contours which is outline of the whiteshape in mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    numberOfPlant = 0
    for count in contours:
        area = cv2.contourArea(count)
        
        #Filter noise so anything larger than 500 pixels shape
        if 500 < area < (totalArea * 0.8):  
            x, y, w, h = cv2.boundingRect(count)
            #Draw rectangle box
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
            #Assign label on box
            cv2.putText(img, "Healthy Plant", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            numberOfPlant = numberOfPlant + 1
    cv2.imwrite(OutputPath, img)
    print(f"Found {numberOfPlant} plant regions. Saved to {OutputPath}\n")
detectPlants("blue_filter1.jpg", "ndvi_map1.jpg", "boxed_plant1.jpg")
detectPlants("blue_filter2.jpg", "ndvi_map2.jpg", "boxed_plant2.jpg")
detectPlants("blue_filter3.jpg", "ndvi_map3.jpg", "boxed_plant3.jpg")
