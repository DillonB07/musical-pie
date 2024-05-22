import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from subsonic import Subsonic, Song, Album

reader = SimpleMFRC522()

client = Subsonic()


def write_data(id: str, name: str, _type: str):
    num = 1 if _type == "track" else 2 if _type == "album" else 3
    to_write = f"{num}|{id}"
    print("Please scan your NFC tag: ")
    reader.write(to_write)
    print(f"{name} has been written to the tag. Please scan your tag again to confirm.")
    data = reader.read()[1].strip()
    if to_write == data:
        print("Data on tag verified and correct!")
    else:
        print(
            f"Woah, it looks like something strange happened and the data wasn't written correctly.\nOriginal: {to_write} - {type(to_write)}\nWritten: {data} - {type(data)}"
        )


def write_track():
    request = input("What song would you like writing to the tag?\n>>> ")
    songs = client.search_song(query=request, single=False)

    if not songs:
        print("No songs found")
        return

    names = "\n".join(
        f"{id}. {name}" for id, name in enumerate([song.title for song in songs], 1)
    )
    print(names)
    valid = False
    while not valid:
        song_input = input("Which song would you like to write to the tag?\n>>> ")
        try:
            song = songs[int(song_input) - 1]
            valid = True
        except ValueError:
            print("Please enter a valid number.")

    write_data(song.id, song.title, "track")


def write_album():
    request = input("What album would you like writing to the tag?\n>>> ")
    albums = client.search_album(query=request, single=False)

    if not albums:
        print("No songs found")
        return

    names = "\n".join(
        f"{id}. {name}" for id, name in enumerate([album.title for album in albums], 1)
    )
    print(names)
    valid = False
    while not valid:
        album_input = input("Which album would you like to write to the tag?\n>>> ")
        try:
            album = albums[int(album_input) - 1]
            valid = True
        except ValueError:
            print("Please enter a valid number.")

    write_data(album.id, album.title, "album")


def write_artist():
    request = input("What artist would you like writing to the tag?\n>>> ")
    artists = client.search_artist(query=request)

    if not artists:
        print("No songs found")
        return

    names = "\n".join(
        f"{id}. {name}"
        for id, name in enumerate([artist.name for artist in artists], 1)
    )
    print(names)
    valid = False
    while not valid:
        artist_input = input("Which artist would you like to write to the tag?\n>>> ")
        try:
            artist = artists[int(artist_input) - 1]
            valid = True
        except ValueError or KeyError:
            print("Please enter a valid number.")

    write_data(artist.id, artist.name, "artist")


if __name__ == "__main__":
    try:
        while True:
            options = """
Music Pie NFC Writer
1. Track
2. Album
3. Artist

Anything else: Exit
            """
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
                    write_track()
                case 2:
                    write_album()
                case 3:
                    write_artist()
                case _:
                    GPIO.cleanup()
                    exit("Goodbye!")
    finally:
        GPIO.cleanup()
        exit("Goodbye!")
