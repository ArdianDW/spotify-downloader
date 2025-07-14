import os
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from ytmusicapi import YTMusic
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
))

def is_spotify_link(text):
    return text.startswith("https://open.spotify.com/track/")

def get_metadata(spotify_url):
    try:
        track = sp.track(spotify_url)
        title = track["name"]
        artist = track["artist"][0]["name"]
        album = track["album"]["name"]
        return {
            "title": title,
            "artist": artist,
            "album": album
        }
    except Exception as e:
        return None
    
def process_song(query_or_url):
    if is_spotify_link(query_or_url):
        metadata = get_metadata(query_or_url)
        if not metadata:
            return {"status": "error", "message": "failed to get metadata"}
        search_query = f"{metadata['artist']} {metadata['title']}"
    else:
        search_query = query_or_url
        metadata = {"title": query_or_url, "artist": "", "album": ""}

    ytmusic = YTMusic()
    results = ytmusic.search(search_query, filter="songs")

    if not results:
        return {"status": "error", "message": "not found"}

    video_id = results[0]['videoId']
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    title = metadata['title']
    artist = metadata['artist']
    album = metadata.get('album', "")

    output_path = f"downloads/{(artist)} - {(title)}.%(ext)s"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': False,
        'ffmpeg_location': 'D:\\ffmpeg\\bin',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320'
        }],
        'postprocessor_args': [
            '-metadata', f'title={title}',
            '-metadata', f'artist={artist}',
            '-metadata', f'album={album}'
        ],
        'prefer_ffmpeg': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    try: 
        audio = MP3(output_path, ID3=ID3)
        audio.add_tags()
    except:
        pass

    try:
        audio = MP3(output_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
    except Exception as e:
        return {"status": "error", "message": f"failed: {str(e)}"}


    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    audio.save()

    return {
        "status": "success",
        "title": title,
        "artist": artist,
        "album": album,
        "youtube_url": youtube_url,
        "file_path": output_path
    }
