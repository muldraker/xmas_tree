"""
NeoPixel strip example for Raspberry Pi Pico running CircuitPython.
Based on various tutorials.

Fires off chasers with randomized colour and decay.
Optional button to fire off the chaser on demand.
Has an idle mode - where the lights will wake up when pressing the button.

REQUIRED MODULES/LIBRARIES:
* CircuitPython
* Adafruit neopixel (neopixel.mpy)
* Adafruit fancyled

REQUIRED HARDWARE:
* Pimoroni Plasma2040 (Or other Raspberry Pi Pico, or even CircuitPython compatible microprocessor).
* RGB NeoPixel LEDs connected to pin GP15 (default, can be configured)
* If not using the Plasma2040:
** Need a ~1000uF capacitor between 5V and GND
** Need a ~300R resistor between GPIO and DATA

TESTED HARDWARE:
* Pimoroni Plasma2040 https://shop.pimoroni.com/products/plasma-2040?variant=39410354847827
** LED Data = GP15
** LED Clock (for DotStar) = GP14
** Switch A = GP12
** Switch B = GP13
** A0 = GP26
** A1 = GP27
** A2 = GP28
** A3 = GP29 (current sense)
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
import supervisor
import time
import adafruit_fancyled.adafruit_fancyled as fancy

# Key parameters you will likely want to change:
pixel_pin = board.GP15              # GPIO pin for talking to the pixels
button_pin = board.GP26 # 12        # GPIO pin for button to trigger a chaser
num_chaser_pixels = 100             # Number of neopixels for the chaser animation
num_top_pixels = 3                  # Number of neopixels for the top animation - if using RGBW will need 1.333 times the actual number of LEDs
top_is_rgbw = True                  # Flag if rgbw LEDs for the top pixels - assumes the chasers are just RGB
max_brightness = 0.30               # Scalar on the max brightness. 1 = max.
time_to_idle_delta = 900            # Extra time in seconds added before idle when pressing the button

# Following parameters are less likely to change
num_sparkles = 1                    # Number of sparkles to track
sparkle_pos = [-1,-1,-1,-1]         # Position of sparkles being added.
sparkle_colour = [(0,0,0), (0,0,0), (0,0,0), (0,0,0)]  # Sparkle colour tracking.
max_sparkle_val = 160               # Maximum colour value for any sparkle
num_chasers = 4                     # Number of chasers
chaser_pos = [-1,-1,-1,-1]          # Chaser position tracking.
chaser_colour = [(0,0,0), (0,0,0), (0,0,0), (0,0,0)]  # Chaser colour tracking.
top_colour_index = 0                # Index for tracking the top colour
top_brightness_max = 255            # Maximum brightness of the top neopixels - this is set when a chaser reaches the top
top_brightness_min = 128            # Minimum brightness of the top neopixels - assume some level of brightness
top_brightness_step = 1             # Decay in brightness for top neopixels
top_brightness = top_brightness_min # Current brightness of the top neopixels
time_to_chaser = 0                  # Millisecond time to add another chaser randomly
min_chaser_time = num_chaser_pixels // (num_chasers - 1) # Minimum time in milliseconds between adding a chaser
max_chaser_time = 180000            # Maximum time in milliseconds between adding a chaser
sparkle_sleep_time = 60             # Time in milliseconds between updates when doing the sparkle
chaser_sleep_time = 20              # Time in milliseconds between updates when doing a chaser
next_loop_time = supervisor.ticks_ms() + sparkle_sleep_time         # Time in milliseconds to act on loop
sparkle_decay_chance_mult = 1       # decay_probability = decay_chance_mult / decay_chance_div
sparkle_decay_chance_div = 15
chaser_decay_chance_mult = 1        # decay_probability = decay_chance_mult / decay_chance_div
chaser_decay_chance_div = 5
sparkle_decay_val_mult = 8          # pixel decay value = pixel_value * decay_val_mult // decay_val_div
sparkle_decay_val_div = 10
chaser_decay_val_mult = 4           # pixel decay value = pixel_value * decay_val_mult // decay_val_div
chaser_decay_val_div = 10
flash_onboard_led = False           # Debug state to flash the onboard LED to check the pico is running
use_idle_timer = True               # Whether to time out to idle. If false will always update the neopixels.
time_to_idle_max = 3600 * 6         # Maximum time in seconds before idle
time_to_idle = time.time()          # Time in seconds before going idle
idle_mode = False                   # Whether we are in idle mode.
time_next_button = next_loop_time   # Time in milliseconds to next check for button value - includes debouce
time_button_debouce = 200           # Time in milliseconds to wait for button debounce

# Initial calculations based on above settings
num_top_pixels_effective = num_top_pixels
if top_is_rgbw:
    # Pad out to include the extra colour
    num_top_pixels_effective = int(num_top_pixels * 1.3) + 1
num_pixels = num_chaser_pixels + num_top_pixels_effective # Total number of neopixels

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

_TICKS_PERIOD = const(1<<29)
_TICKS_MAX = const(_TICKS_PERIOD-1)
_TICKS_HALFPERIOD = const(_TICKS_PERIOD//2)


# Fix the wrap around with supervisor.ticks_ms
# From https://docs.circuitpython.org/en/latest/shared-bindings/supervisor/index.html
def ticks_add(ticks, delta):
    "Add a delta to a base number of ticks, performing wraparound at 2**29ms."
    return (ticks + delta) % _TICKS_PERIOD


def ticks_diff(ticks1, ticks2):
    "Compute the signed difference between two ticks values, assuming that they are within 2**28 ticks"
    diff = (ticks1 - ticks2) & _TICKS_MAX
    diff = ((diff + _TICKS_HALFPERIOD) & _TICKS_MAX) - _TICKS_HALFPERIOD
    return diff


def ticks_less(ticks1, ticks2):
    "Return true if ticks1 is less than ticks2, assuming that they are within 2**28 ticks"
    return ticks_diff(ticks1, ticks2) < 0


def update_top():
    """Update the top pixels."""
    global pixels, top_brightness, top_colour_index
    color = fancy.CHSV(top_colour_index, 96, top_brightness)
    color_g = fancy.gamma_adjust(color)
    if top_is_rgbw:
        red = int(color_g[0]*256)
        green = int(color_g[1]*256)
        blue = int(color_g[2]*256)
        white = min(red, green, blue)
        red -= white
        green -= white
        blue -= white
        colours = [green, red, blue, white]
        colour_ind = 0
        max_ind = 4 * num_top_pixels
        for ind in range(num_top_pixels_effective):
            base_ind = 3 * ind
            # Note: the first two elements get flipped, effectively   g,r,b -> r,g,b
            val_0 = colours[(base_ind+1)%4] if base_ind + 1 < max_ind else 0
            val_1 = colours[(base_ind+0)%4] if base_ind + 0 < max_ind else 0
            val_2 = colours[(base_ind+2)%4] if base_ind + 2 < max_ind else 0
            pixels[ind+num_chaser_pixels] = (val_0,val_1,val_2)
    else:
        packed = color_g.pack()
        for ind in range(num_chaser_pixels, num_chaser_pixels + num_top_pixels):
            pixels[ind] = packed
    if top_brightness > top_brightness_min:
        top_brightness -= top_brightness_step
    top_colour_index += 1


def reach_top():
    """Event for the top pixels animation.
    Happens when a chaser reaches the top.
    """
    global top_brightness
    top_brightness = top_brightness_max


def add_chaser():
    """Will check if there is enough space since the last chaser."""
    global chaser_pos, time_to_chaser
    last_chaser = num_chaser_pixels #  + min_chaser_time
    for ind in range(num_chasers):
        if chaser_pos[ind] == -1 and (last_chaser > min_chaser_time or last_chaser == -1):
            chaser_pos[ind] = 0
            #chaser_colour[ind] = (255,255,255)
            chaser_colour[ind] = (random.randrange(64,255),random.randrange(64,255),random.randrange(64,255))
            #chaser_colour[ind] = (128,64,32)
            time_to_chaser = ticks_add(supervisor.ticks_ms(), random.randrange(min_chaser_time, max_chaser_time))
            break
        elif -1 < chaser_pos[ind] < last_chaser:
            last_chaser = chaser_pos[ind]


def progress_chasers():
    """Increment the chaser positions.
    Chaser decay is handled in decay_leds.
    """
    global chaser_pos, pixels
    for ind in range(num_chasers):
        if chaser_pos[ind] >= 0 and chaser_pos[ind] < num_chaser_pixels:
            pixels[chaser_pos[ind]] = chaser_colour[ind]
            chaser_pos[ind] += 1
            if chaser_pos[ind] >= num_chaser_pixels:
                chaser_pos[ind] = -1
                reach_top()


def add_sparkle(decay_chance_mult, decay_chance_div):
    """Add some individual pixel sparkles."""
    global sparkle_pos, sparkle_colour, pixels
    for ind in range(num_sparkles):
        if random.randrange(decay_chance_div) < decay_chance_mult:
            if sparkle_pos[ind] == -1:
                sparkle_pos[ind] = random.randrange(num_chaser_pixels)
                sparkle_colour[ind] = (random.randrange(32,64),random.randrange(32,60),random.randrange(32,56))
            #pixels[sparkle_pos[ind]] = sparkle_colour[ind]
            pixel_r = pixels[sparkle_pos[ind]][0] + sparkle_colour[ind][0]
            pixel_g = pixels[sparkle_pos[ind]][1] + sparkle_colour[ind][1]
            pixel_b = pixels[sparkle_pos[ind]][2] + sparkle_colour[ind][2]
            pixels[sparkle_pos[ind]] = (pixel_r, pixel_g, pixel_b)
            # Check if the sparkle has maxed out. If so, stop tracking it and let it decay.
            if pixels[sparkle_pos[ind]][0] > max_sparkle_val or pixels[sparkle_pos[ind]][1] > max_sparkle_val or pixels[sparkle_pos[ind]][2] > max_sparkle_val:
                sparkle_pos[ind] = -1


def decay_leds(decay_chance_mult, decay_chance_div, decay_val_mult, decay_val_div):
    """Decay the pixels with a hint of randomness for a sparkle effect."""
    global pixels
    if decay_chance_mult == 0 or decay_chance_div == 0:
        return
    for ind in range(num_chaser_pixels):
        if sum(pixels[ind]) > 0 and ind not in sparkle_pos:
            if random.randrange(decay_chance_div) < decay_chance_mult:
                pixel_r = (pixels[ind][0]*decay_val_mult)//decay_val_div
                pixel_g = (pixels[ind][1]*decay_val_mult)//decay_val_div
                pixel_b = (pixels[ind][2]*decay_val_mult)//decay_val_div
                pixels[ind] = (pixel_r, pixel_g, pixel_b)
                if sum(pixels[ind]) < 3:
                    pixels[ind] = (0,0,0)   # Just switch off


def add_time_to_idle():
    """Add time to the timer before going to idle.
    This uses time (seconds) rather than ticks_ms (milliseconds) so less concerned by wrap-around.
    """
    global time_to_idle, idle_mode
    idle_mode = False
    if use_idle_timer:
        time_now = time.time()
        if time_to_idle < time_now:
            time_to_idle = time_now
        time_to_idle += time_to_idle_delta
        current_time_to_idle_max = time.time() + time_to_idle_max
        if time_to_idle > current_time_to_idle_max:
            time_to_idle = current_time_to_idle_max


def is_idle():
    """Check if we are (or should be) in idle state.
    This uses time (seconds) rather than ticks_ms (milliseconds) so less concerned by wrap-around.
    """
    global idle_mode, time_to_idle
    # Check if idle mode already set
    if not use_idle_timer:
        return False
    if idle_mode:
        return True
    # See if the idle mode timer has run out
    if time_to_idle < time.time():
        print("Now idle!")
        idle_mode = True
        # Turn off the pixels.
        pixels.fill((0,0,0))
        pixels.show()
        return True
    return False


def is_button_clicked():
    """Check if the button is clicked. Include a debounce timer.
    Works on ticks_ms (milliseconds)"""
    global time_next_button
    # Onboard Plasma2040 buttons switch to GND, so low value when triggered
    time_now = supervisor.ticks_ms()
    if ticks_less(time_next_button, time_now) and not button.value:
        print("Button!")
        time_next_button = ticks_add(time_now, time_button_debouce)
        return True
    else:
        return False


def update_loop():
    """Main loop function."""
    global next_loop_time, pixels, time_to_chaser, time_to_idle
    # Check the button before checking for idle - as the button can get us out of idle.
    if is_button_clicked():
        add_chaser()
        add_time_to_idle()
    elif is_idle():
        return
    # Rather than sleep, check the timer.
    time_now = supervisor.ticks_ms() # time.time()
    # Check if we have active chasers.
    active_chasers = sum(chaser_pos) > num_chasers * -1
    sleep_time = chaser_sleep_time if active_chasers else sparkle_sleep_time
    # Check if we want to do an update to the LEDs
    if ticks_less(time_now, next_loop_time):
        return
    else:
        next_loop_time = time_now + sleep_time
    # Get the LED decay values.
    decay_chance_div = chaser_decay_chance_div if active_chasers else sparkle_decay_chance_div
    decay_chance_mult = chaser_decay_chance_mult if active_chasers else sparkle_decay_chance_mult
    decay_val_div = chaser_decay_val_div if active_chasers else sparkle_decay_val_div
    decay_val_mult = chaser_decay_val_mult if active_chasers else sparkle_decay_val_mult
    # Check if we randomly want to add a chaser.
    if ticks_less(time_to_chaser, time_now):
        add_chaser()
    # Progress the chasers
    progress_chasers()
    # Add a random twinkle to the LEDs if no active chasers
    if not active_chasers and num_chaser_pixels > 0:
        add_sparkle(decay_chance_div, decay_chance_mult)
    # Decay the pixels with a hint of randomness for a sparkle effect.
    decay_leds(decay_chance_mult, decay_chance_div, decay_val_mult, decay_val_div)
    # Update the top pixels
    update_top()
    # Show the updates.
    pixels.show()


# Start off with a chaser and some idle time
add_chaser()
add_time_to_idle()

while True:
    if flash_onboard_led:
        led.value = not led.value
    update_loop()
    #time.sleep(sleep_time)