# Program: make_Heatmap.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
import cv2
import numpy as np

def generateHeatmap(ndvi_path, output_path):
    ndvi = cv2.imread(ndvi_path, cv2.IMREAD_GRAYSCALE)
    if ndvi is not None:
        heatmap = cv2.applyColorMap(ndvi, cv2.COLORMAP_JET)
        cv2.imwrite(output_path, heatmap)
        print(f"Saved {output_path}")

generateHeatmap("ndvi_map1.jpg", "heatmap1.jpg")
generateHeatmap("ndvi_map2.jpg", "heatmap2.jpg")
generateHeatmap("ndvi_map3.jpg", "heatmap3.jpg")