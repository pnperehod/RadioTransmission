from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
import discogs

mp4_tag = {}


def fill_mp4_tags(song_title, fname, client):
    artist = song_title.split(' - ')[0]
    title = song_title.split(' - ')[1]
    discogs.get_album_cover(song_title, client)
    album_name, year = discogs.get_release_info()

    audio = MP4(fname)
    audio["\xa9nam"] = title
    audio["\xa9ART"] = artist
    audio["\xa9alb"] = album_name
    audio["\xa9day"] = year
    with open('cover.jpg', 'rb') as pic:
        audio["covr"] = [MP4Cover(pic.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()
    print(f'{artist} - {title} [{album_name}] (p){year}')





