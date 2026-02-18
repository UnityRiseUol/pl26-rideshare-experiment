# Program: draw_Boxes.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
# Program: salvage_data.py
# Description: Uses Min-Max Normalization to recover NDVI signals 
#              from AWB-corrupted static JPG images.

import cv2
import numpy as np

def salvage_image(input_path, output_box_path, output_mask_path):
    print(f"Salvaging data for: {input_path}...")
    
    #Load original colour image and greyscale NDVI image
    img = cv2.imread(input_path)
    if img is None:
        print(f"Failed to load {input_path}")
        return
    b, g, r = cv2.split(img)
    r = r.astype(float)
    b = b.astype(float)
    
    numerator = r - b
    denominator = (r + b) + 1e-5
    ndvi = numerator / denominator
    
    #Normalise to 0-255 range
    ndvi_base = ((ndvi + 1) / 2) * 255
    ndvi_8bit = ndvi_base.astype(np.uint8)

    #Min-Max Contrast Stretching to remove auto white balance
    ndvi_stretched = cv2.normalize(ndvi_8bit, None, 0, 255, cv2.NORM_MINMAX)

    #Thresholding
    #Set 140 to be baselibe threshold for "alive plant"
    #Above 140 means set to 255 white and thr rest is 0 black.
    _, mask = cv2.threshold(ndvi_stretched, 200, 255, cv2.THRESH_BINARY)
    
    #Save the stretched mask so you can see the magic!
    cv2.imwrite(output_mask_path, mask)

    #Find Contours which is outline of the whiteshape in mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    total_area = img.shape[0] * img.shape[1]
    numberOfPlant = 0

    for count in contours:
        area = cv2.contourArea(count)
        
        # Filter noise and giant background boxes
        if 500 < area < (total_area * 0.8):  
            x, y, w, h = cv2.boundingRect(count)
            aspectRatio = float(h) / float(w)
            
            if aspectRatio < 3.0:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
                cv2.putText(img, "Healthy Plant", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                numberOfPlant += 1
            
    cv2.imwrite(output_box_path, img)
    print(f"Found {numberOfPlant} plants. Saved to {output_box_path}\n")

#Output salvaged images after removed AWB from them
salvage_image("blue_filter1.jpg", "salvaged_box1.jpg", "salvaged_mask1.jpg")
salvage_image("blue_filter2.jpg", "salvaged_box2.jpg", "salvaged_mask2.jpg")
salvage_image("blue_filter3.jpg", "salvaged_box3.jpg", "salvaged_mask3.jpg")