"""
NeoPixel strip example for Raspberry Pi Pico running CircuitPython.
Based on various tutorials.

Fires off chasers with randomized colour and decay.
Optional button to fire off the chaser on demand.

REQUIRED MODULES/LIBRARIES:
* CircuitPython
* Adafruit neopixel (neopixel.mpy)

REQUIRED HARDWARE:
* Pimoroni Plasma2040 (Or other Raspberry Pi Pico, or even CircuitPython compatible microprocessor).
* RGB NeoPixel LEDs connected to pin GP15 (default, can be configured)
* If not using the Plasma2040:
** Need a ~1000uF capacitor between 5V and GND
** Need a ~300R resistor between GPIO and DATA

TESTED HARDWARE:
* Pimoroni Plasma2040 https://shop.pimoroni.com/products/plasma-2040?variant=39410354847827
** Data = GP15
** Switch A = GP12
** Switch B = GP13
* QTY3 - Adafruit NeoPixel Slim LED Dot Strand - 20 LEDs at 2" Pitch
** 60 pixels
** max brightness 0.30
** sleep time = 0.015 because the LEDs are further spaced out
** Running off of 5V 2A power supply
* QTY1 - Adafruit NeoPixel LED Side Light Strip - Black 120 LED
** Used for another project, but used here for quick development.
** 120 pixels
** max brightness 0.02 (for testing)
** sleep time = 0.03 because the LEDs are close together
** Running off computer USB

OPTIONAL HARDWARE:
* Button between GND and GP12
"""
import board
import digitalio
import neopixel
import random
import time
#from rainbowio import colorwheel

pixel_pin = board.GP15              # GPIO pin for talking to the pixels
button_pin = board.GP12             # GPIO pin for button to trigger a chaser
num_pixels = 60                     # Number of neopixels playing with
max_brightness = 0.30               # Scalar on the max brightness. 1 = max.
num_chaser_pos = 4                  # Number of chasers
chaser_pos = [-1,-1,-1,-1]          # Chaser position tracking.
chaser_colour = [(0,0,0), (0,0,0), (0,0,0), (0,0,0)]  # Chaser colour tracking.
time_to_chaser = 0
min_chaser_time = num_pixels // (num_chaser_pos - 1) # Minimum time between adding a chaser
max_chaser_time = 6000              # Maximum time between adding a chaser
sleep_time = 0.015                   # Time in seconds between updates
decay_chance_mult = 1               # decay_chance = decay_chance_mult in decay_chance_div
decay_chance_div = 4
decay_val_mult = 1                  # pixel decay value = pixel_value * decay_val_mult // decay_val_div
decay_val_div = 2
flash_onboard_led = False           # Debug to check the pico is running.

# Define and initialize the onboard LED Pin - for heartbeat checking.
led = digitalio.DigitalInOut(board.LED) # board.GP25 # Onboard LED
led.direction = digitalio.Direction.OUTPUT

# Define and  initialize the chaser button
button = digitalio.DigitalInOut(button_pin)
button.switch_to_input(pull=digitalio.Pull.UP)  # Onboard Plasma2040 buttons switch to GND - so pull up.
#button.direction = digitalio.Direction.INPUT

# Define and  initialize the neopixels
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, auto_write=False)
pixels.brightness = max_brightness
pixels.fill((0, 0, 0))  # Clear the pixels
pixels.show()


def add_chaser():
    """Will check if there is enough space since the last chaser."""
    last_chaser = num_pixels #  + min_chaser_time
    for ind in range(num_chaser_pos):
        if chaser_pos[ind] == -1 and (last_chaser > min_chaser_time or last_chaser == -1):
            chaser_pos[ind] = 0
            #chaser_colour[ind] = (255,255,255)
            chaser_colour[ind] = (random.randrange(64,255),random.randrange(64,255),random.randrange(64,255))
            break
        elif chaser_pos[ind] < last_chaser:
            last_chaser = chaser_pos[ind]


def update_loop():
    global time_to_chaser
    # See if we can add another chaser
    # Onboard Plasma2040 buttons switch to GND, so low value when triggered
    if time_to_chaser <= 0 or not button.value:
        # reset the counter, and then add a chaser
        time_to_chaser = random.randrange(min_chaser_time, max_chaser_time)
        add_chaser()
    else:
        time_to_chaser -= 1
    # Progress the chasers
    for ind in range(num_chaser_pos):
        if chaser_pos[ind] >= 0 and chaser_pos[ind] < num_pixels:
            pixels[chaser_pos[ind]] = chaser_colour[ind]
            chaser_pos[ind] += 1
            if chaser_pos[ind] >= num_pixels:
                chaser_pos[ind] = -1
    # Decay the pixels with a hint of randomness for a sparkle effect.
    for ind in range(num_pixels):
        if sum(pixels[ind]) > 0 and decay_chance_mult > 0 and decay_chance_div > 0:
            if random.randrange(decay_chance_div) < decay_chance_mult:
                pixels[ind] = (pixels[ind][0]*decay_val_mult//decay_val_div, pixels[ind][1]*decay_val_mult//decay_val_div, pixels[ind][2]*decay_val_mult//decay_val_div)
    pixels.show()


while True:
    if flash_onboard_led:
        led.value = not led.value
    update_loop()
    time.sleep(sleep_time)