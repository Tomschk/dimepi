#!/usr/bin/env python

from keypad import Keypad
import RPi.GPIO as GPIO
import asyncio
import logging
import os
from pygame import mixer
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

music_directory = config['general']['music_directory']  # Directory where MP3s are stored

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

# Initialize Pygame mixer
mixer.init()

async def jukebox_handler(queue, keypad):
    while True:
        track = await queue.get()
        queue.task_done()

        track_path = os.path.join(music_directory, f"{track}.mp3")
        
        logging.info(f"Looking for track at: {track_path}")  # Add this line to log the path
        
        if os.path.exists(track_path):
            logging.info(f"Playing song: {track}")
            mixer.music.load(track_path)
            mixer.music.play()
            
            # Turn on the credit light for 5 seconds
            asyncio.create_task(keypad.blink_credit_light())
            
            while mixer.music.get_busy():  # Wait until song finishes
                await asyncio.sleep(1)
        else:
            logging.error(f"Track {track} not found")

def main():
    try:
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)

        # Add blink_credit_light method to Keypad class
        async def blink_credit_light():
            keypad.set_credit_light_on()
            await asyncio.sleep(5)
            keypad.set_credit_light_off()
        
        # Attach the new method to the Keypad instance
        setattr(keypad, "blink_credit_light", blink_credit_light)

        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_key_combination())
        loop.create_task(jukebox_handler(keypad_queue, keypad))
        loop.run_forever()
    
    finally:
        GPIO.cleanup()
        mixer.quit()
        loop.close()

if __name__ == "__main__":
    main()
