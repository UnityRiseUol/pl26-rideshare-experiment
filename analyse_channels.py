# Program: analyse_channels.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
import cv2
import numpy as np

def analyseImage(path):
    img = cv2.imread(path)

    if img is None:
        print(f"Failed to load {path}!")
        return

    print(f"Analysis for {path}:")

    channel_names = ["Blue", "Green", "Red"]
    for i, name in enumerate(channel_names):
        channel = img[:, :, i]
        print(f"{name} channel:")
        print(f" Mean: {np.mean(channel):.2f}")
        print(f" Standard Deviation: {np.std(channel):.2f}")
        print(f" Minimum: {np.min(channel):.2f}")
        print(f" Maximum: {np.max(channel):.2f}")
        print()

analyseImage("no_filter.jpg")
analyseImage("blue_filter.jpg")        

