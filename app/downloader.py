import os
import re
import yt_dlp
import requests
import shutil
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

def clean_url(url):
    return url.split('?')[0]

def is_spotify_link(text):
    return "open.spotify.com/track/" in text

def is_spotify_playlist(text):
    text = clean_url(text)
    return re.search(r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)", text) is not None

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_metadata(spotify_url):
    try:
        match = re.search(r"track/([a-zA-Z0-9]+)", spotify_url)
        if not match:
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
        print(f"Metadata error: {e}")
        return None

def download_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
    except:
        pass
    return None

def process_song(url, custom_folder="downloads"):
    os.makedirs(custom_folder, exist_ok=True)

    if is_spotify_link(url):
        metadata = get_metadata(url)
        if not metadata:
            return {"status": "error", "message": "failed to get metadata"}
        search_query = f"{metadata['artist']} {metadata['title']}"
    else:
        return {"status": "error", "message": "invalid url"}

    ytmusic = YTMusic()
    results = ytmusic.search(search_query, filter="songs")

    if not results:
        return {"status": "error", "message": "not found"}

    video_id = results[0]['videoId']
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    title = sanitize_filename(metadata['title'])
    artist = sanitize_filename(metadata['artist'])
    album = sanitize_filename(metadata.get('album', ""))
    cover_url = metadata.get("cover_url")

    filename = f"{artist} - {title}.mp3"
    output_path = os.path.join(custom_folder, filename)
    temp_output = os.path.join(custom_folder, "temp.%(ext)s")

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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        return {"status": "error", "message": f"yt-dlp error: {e}"}

    temp_mp3 = os.path.join(custom_folder, "temp.mp3")
    try:
        if os.path.exists(temp_mp3):
            os.rename(temp_mp3, output_path)
        else:
            return {"status": "error", "message": "file conversion failed"}
    except Exception as e:
        return {"status": "error", "message": f"rename error: {e}"}

    # Add tags
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
        return {"status": "error", "message": f"tagging error: {str(e)}"}

    return {
        "status": "success",
        "title": title,
        "artist": artist,
        "album": album,
        "youtube_url": youtube_url,
        "file_path": output_path
    }

def process_playlist(playlist_url):
    match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
    if not match:
        return {"status": "error", "message": "not found"}

    playlist_id = match.group(1)
    try:
        playlist = sp.playlist(playlist_id)
        tracks = playlist["tracks"]["items"]
        playlist_name = sanitize_filename(playlist['name'])
        folder_path = os.path.join("downloads", playlist_name)
        os.makedirs(folder_path, exist_ok=True)

        results = []
        for item in tracks:
            track = item.get("track")
            if not track or not track.get("id"):
                results.append({"status": "error", "message": "invalid data"})
                continue

            track_url = f"https://open.spotify.com/track/{track['id']}"
            result = process_song(track_url, custom_folder=folder_path)
            results.append(result)

        base_dir = os.path.dirname(folder_path)        
        root_dir = os.path.basename(folder_path)  
        zip_path = shutil.make_archive(
            os.path.join(base_dir, root_dir), 'zip', base_dir, root_dir
        )

        shutil.rmtree(folder_path)

        return {
            "status": "success",
            "playlist_name": playlist_name,
            "zip_path": zip_path,
            "total_tracks": len(results),
            "tracks": results,
            "download_link": f"/downloads/{playlist_name}.zip"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
