#!/usr/bin/env python

from keypad import Keypad
import RPi.GPIO as GPIO
import asyncio
import logging
import os
import random
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
shuffle_mode = False  # Flag to indicate if we are in shuffle mode
shuffle_task = None   # Task to handle shuffle playback

async def play_shuffle():
    global shuffle_mode
    while shuffle_mode:
        song_list = [f for f in os.listdir(music_directory) if f.endswith('.mp3')]
        if not song_list:
            logging.error("No songs found in the directory for shuffle mode.")
            break
        random.shuffle(song_list)
        for song in song_list:
            if not shuffle_mode:
                return  # Stop shuffle if mode is turned off
            song_path = os.path.join(music_directory, song)
            logging.info(f"Playing shuffled song: {song}")
            mixer.music.load(song_path)
            mixer.music.play()
            while mixer.music.get_busy() and shuffle_mode:
                await asyncio.sleep(1)

async def jukebox_handler(queue, keypad):
    global shuffle_mode, shuffle_task
    while True:
        track = await queue.get()
        queue.task_done()

        # Turn on the credit light for 5 seconds with each selection
        await keypad.blink_credit_light()

        if track == "F4":
            if not shuffle_mode:
                shuffle_mode = True
                logging.info("Entering shuffle mode.")
                shuffle_task = asyncio.create_task(play_shuffle())
        elif track == "F3":
            logging.info("Stopping all music and clearing queue immediately.")
            mixer.music.stop()
            shuffle_mode = False
            if shuffle_task:
                shuffle_task.cancel()
            while not queue.empty():
                queue.get_nowait()
                queue.task_done()
            continue  # Skip the rest of the loop to prevent playing any queued songs
        else:
            logging.info("Stopping any currently playing song before playing new selection.")
            mixer.music.stop()
            if shuffle_mode:
                logging.info("Exiting shuffle mode.")
                shuffle_mode = False
                if shuffle_task:
                    shuffle_task.cancel()
            
            track_path = os.path.join(music_directory, f"{track}.mp3")
            
            logging.info(f"Looking for track at: {track_path}")
            
            if os.path.exists(track_path):
                logging.info(f"Playing song: {track}")
                mixer.music.load(track_path)
                mixer.music.play()
                
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
