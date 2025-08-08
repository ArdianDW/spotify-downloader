from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from app.downloader import process_song, process_playlist, is_spotify_link, is_spotify_playlist

app = FastAPI()

app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

@app.get("/")
def root():
    return {"message": "downloader is running"}

@app.get("/download")
def download(query: str = Query(..., description="spotify link")):
    if not query.startswith("https://open.spotify.com/"):
        raise HTTPException(status_code=400, detail="invalid url kimak")

    if is_spotify_playlist(query):
        result = process_playlist(query)
    elif is_spotify_link(query):
        result = process_song(query)
    else:
        raise HTTPException(status_code=400, detail="invalid url")

    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result
