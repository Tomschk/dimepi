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
stop_music = False    # Flag to indicate if music should be stopped immediately

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
    global shuffle_mode, shuffle_task, stop_music
    while True:
        if stop_music:
            # Stop all music and clear the queue immediately
            logging.info("Stopping all music and clearing queue immediately due to F3
