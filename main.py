#!/usr/bin/env python
import os
import pygame
import asyncio
import logging
import RPi.GPIO as GPIO
import board
from keypad import Keypad

# Configuration
MUSIC_DIR = "/home/pi/music"  # Directory where MP3 files are stored
COINSLOT_GPIO_PIN = 17  # Adjust based on your setup
CABINET_LIGHTS_COLOR = (255, 0, 0)  # RGB Color for the cabinet lights

# Initialize logging
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')

# Initialize pygame mixer
pygame.mixer.init()

async def jukebox_handler(queue, keypad):
    while True:
        keypad.set_credit_light_on()
        output = await queue.get()
        queue.task_done()
        
        track_path = os.path.join(MUSIC_DIR, f"{output}.mp3")
        if os.path.isfile(track_path):
            logging.info(f"Playing: {track_path}")
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(1)  # Wait until song finishes
        else:
            logging.error(f"Track {output}.mp3 not found!")

        keypad.set_credit_light_off()

# Handle coin slot input
def coinslot_callback(channel):
    logging.info("Coin inserted - Incrementing credits")
    keypad.set_credit_light_on()

def setup_coinslot():
    GPIO.cleanup()  # Ensure a clean GPIO state before setting up pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(COINSLOT_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(COINSLOT_GPIO_PIN, GPIO.FALLING, 
                          callback=coinslot_callback, bouncetime=200)

def main():
    loop = asyncio.get_event_loop()  # Initialize the event loop first
    try:
        keypad_queue = asyncio.Queue()
        global keypad
        keypad = Keypad(keypad_queue)
        setup_coinslot()

        # Create and run asynchronous tasks
        loop.create_task(keypad.get_key_combination())
        loop.create_task(jukebox_handler(keypad_queue, keypad))
        loop.run_forever()
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    
    finally:
        GPIO.cleanup()  # Clean up GPIO pins when done
        if loop.is_running():  # Ensure the loop is running before stopping
            loop.stop()
        loop.close()

if __name__ == "__main__":
    main()
