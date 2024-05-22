import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from subsonic import Subsonic, Song, Album
from threading import Thread
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
from ADCDevice import ADCDevice, PCF8591, ADS7830

import alsaaudio
import vlc
import time
import random
import queue
import subprocess
import math as maths

reader = SimpleMFRC522()

client = Subsonic()
music_queue: queue.Queue = queue.Queue()
current_song = None
player = vlc.Instance()
media_player = player.media_player_new()
media_player.audio_set_volume(50)
PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
adc = ADCDevice()

try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print("I2C Address Error !")
        exit(1)
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)
mcp.output(3, 1)
lcd.begin(16, 2)


def setup_adc():
    global adc
    if adc.detectI2C(0x48):  # Detect the pcf8591.
        adc = PCF8591()
    elif adc.detectI2C(0x4B):  # Detect the ads7830
        adc = ADS7830()
    else:
        print(
            "No correct I2C address found, \n"
            "Please use command 'i2cdetect -y 1' to check the I2C address! \n"
            "Program Exit. \n"
        )
        exit(-1)


def main():
    options = """
---Menu---
1. Skip Song
2. Toggle Play/Pause

3. Set audio device

0. Exit

Please enter a number
>>> """
    while True:
        valid = False
        while not valid:
            inp = input(options)
            try:
                ans = int(inp)
                valid = True
            except ValueError:
                print("Please enter a valid number")

        match ans:
            case 1:
                next()
            case 2:
                toggle_play()
            case 3:
                set_audio_device()
            case 0:
                exit("Goodbye!")


def read_data():
    # while True: 
    id, text = reader.read()
    media_type, media_id = text.strip().split("|")
    match media_type:
        case "1":
            track = client.get_song(media_id)
            if track.title:
                clear_queue()
                music_queue.put(track)
                print(f"Added {track.title} - {track.artist} to queue")
        case "2":
            album = client.get_album(media_id)
            if album.songs:
                clear_queue()
                for track in album.songs:
                    music_queue.put(track)
        case "3":
            artist = client.get_artist(media_id)
            albums = client.search_album(artist.name, single=False)
            songs = []
            if not albums:
                print("No albums found")
            elif type(albums) == Album:
                if albums.songs:
                    for song in albums.songs:
                        music_queue.put(song)
            else:
                for album in albums:
                    if album.songs:
                        songs.extend(album.songs)
            clear_queue()
            random.shuffle(songs)
            for song in songs:
                music_queue.put(song)
        case _:
            print("Invalid media type")


def next():
    media_player.stop()


def toggle_play():
    if media_player.is_playing():
        media_player.pause()
    else:
        media_player.play()


def check_queue_and_play():
    global media_player
    global music_queue
    global current_song
    scrobbled = False

    while True:
        length = media_player.get_length() / 1000
        current_time = media_player.get_time() / 1000
        if (
            not media_player.is_playing()
            and music_queue.qsize() > 0
            and media_player.get_state() != vlc.State.Paused
        ):
            current_song = music_queue.get()
            while not current_song.title:
                current_song = music_queue.get()
            print(f"Now playing: {current_song.title} - {current_song.artist}")
            update_display(current_song.title, current_song.artist)
            media = player.media_new(current_song.stream_url)
            media_player.set_media(media)
            media_player.play()
            client.scrobble(current_song.id, False)
            scrobbled = False
        elif (
            media_player.is_playing()
            and (current_time / length) > 0.5
            and not scrobbled
        ):
            client.scrobble(current_song.id, True)
            scrobbled = True
        else:
            time.sleep(1)


def clear_queue():
    global music_queue
    music_queue = queue.Queue()


def update_display(line1: str = "", line2: str = ""):
    lcd.clear()
    lcd.setCursor(0, 0)
    lcd.message(line1)
    lcd.setCursor(0, 1)
    lcd.message(line2)

def update_volume():
    global mixer
    while True: 
        volume = adc.analogRead(0)
        mixer.setvolume(maths.floor(volume/254*100))

def set_audio_device():
    global mixer
    devices = alsaaudio.cards()
    print(''.join(f"{i}. {device}\n" for i, device in enumerate(devices, 1)))
    valid = False
    while not valid:
        try:
            dev = int(input("Please enter the number of the output device: "))
            valid = True
        except ValueError:
            print("Please enter a valid number.")

    mixer = alsaaudio.Mixer('PCM', device=f'hw:{devices[dev-1]}')


if __name__ == "__main__":
    try:
        print(alsaaudio.mixers())
        print(alsaaudio.cards())
        # print(alsaaudio.mixers(device='hw:P2'))
        set_audio_device()
        setup_adc()
        update_display("Musical Pie", "By DillonB07")
        player_thread = Thread(target=check_queue_and_play, daemon=True)
        reader_thread = Thread(target=read_data, daemon=True)
        volume_thread = Thread(target=update_volume, daemon=True)

        player_thread.start()
        reader_thread.start()
        volume_thread.start()
        main()
    finally:
        GPIO.cleanup()
        lcd.clear()
        adc.close()
