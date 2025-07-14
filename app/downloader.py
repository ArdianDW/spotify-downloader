import os
import re
import yt_dlp
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
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
    return re.search(r"open\.spotify\.com/.*/track/([a-zA-Z0-9]+)", text) is not None

def get_metadata(spotify_url):
    try:
        match = re.search(r"track/([a-zA-Z0-9]+)", spotify_url)
        if not match:
            print("not found.")
            return None
        
        track_id = match.group(1)
        track = sp.track(track_id)

        title = track["name"]
        artist = track["artists"][0]["name"]
        album = track["album"]["name"]
        cover_url = track["album"]["images"][0]["url"] if track["album"]["images"] else None

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "cover_url": cover_url
        }
    except Exception as e:
        print(f"Failed to get metadata: {e}")
        return None
    
def download_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
    except:
        pass
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
    cover_url = metadata.get("cover_url")

    filename = f"{artist} - {title}.mp3"
    output_path = os.path.join("downloads", filename)
    temp_output = os.path.join("downloads", "temp.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_output,
        'quiet': False,
        'ffmpeg_location': 'D:\\ffmpeg\\bin',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320'
        }],
        'outtmpl_na_placeholder': 'unknown',
        'prefer_ffmpeg': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    temp_mp3 = os.path.join("downloads", "temp.mp3")
    if os.path.exists(temp_mp3):
        os.rename(temp_mp3, output_path)
    else:
        return {"failed"}

    try:
        audio = MP3(output_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=album))

        if cover_url:
            image_data = download_image(cover_url)
            if image_data:
                audio.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=image_data
                ))

        audio.save()
    except Exception as e:
        return {"status": "error", "message": f"Tagging error: {str(e)}"}

    return {
        "status": "success",
        "title": title,
        "artist": artist,
        "album": album,
        "youtube_url": youtube_url,
        "file_path": output_path
    }
