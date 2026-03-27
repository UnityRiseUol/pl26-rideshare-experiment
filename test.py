
# Program: test.py
# Author:
# Module:
# Email:
# Student Number:
# -----------------------------------------------------------------------------------------------------------------------------
# Code
from gpiozero import Button, LED, TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

#Configuration
BUTTON_PIN = 27#Gray wire
GREEN_LED = 22#Green wire
RED_LED = 23#Redwire
BUZZER_PIN = 24#Orange wire

button = Button(BUTTON_PIN, pull_up=True) 
green = LED(GREEN_LED)
red = LED(RED_LED)
buzzer = TonalBuzzer(BUZZER_PIN)

print("Hardware test running!")
print("Press the button!")
print("Press Ctrl+C to exit!")

try:
    while True:
        if button.is_pressed:
            print("Button Pressed! Playing note A4...")
            green.on()
            red.on()
            
            buzzer.play(Tone("A4"))
            
            sleep(0.5) 
        else:
            green.off()
            red.off()
            buzzer.stop()
            
        sleep(0.05)

except KeyboardInterrupt:
    print("\nTest stopped!")
    green.off()
    red.off()
    buzzer.stop()