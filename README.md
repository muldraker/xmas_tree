# Xmas Tree - Neopixel style
### Hayden Watkins, 2022

NeoPixel strip example for Raspberry Pi Pico running CircuitPython. I have this in mind to light up a christmas tree - I wanted to have a randomized rocket/sparkle/comet trail going up the tree every so often. With an optional bonus button for my daughter to interact and trigger the comet.


### References

Based on various tutorials and ramblings, but primarily:
* CircuitPython https://learn.adafruit.com/welcome-to-circuitpython/overview
* Dave's Garage Comet Effect https://www.youtube.com/watch?v=yM5dY7K2KHM


### Requirements

REQUIRED MODULES/LIBRARIES:
* CircuitPython
* Adafruit neopixel (neopixel.mpy)

REQUIRED HARDWARE:
* RGB NeoPixel LEDs connected to pin GP0 (default)
* Need a ~1000uF capacitor between 5V and GND
* Need a ~300R resistor between GPIO and DATA

OPTIONAL HARDWARE:
* Button between 3V3 and GP13


### Development

Side-goal of the project is to familiarize myself with CircuitPython (maybe MicroPython later) with a "simple" project.
