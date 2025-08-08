from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from app.downloader import is_spotify_link, is_spotify_playlist, process_song, process_playlist
from urllib.parse import unquote

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "downloader is running."}


@app.get("/download")
async def download(query: str = Query(..., description="spotify link")):
    decoded_query = unquote(query)

    if is_spotify_link(decoded_query):
        result = process_song(decoded_query)
        return result

    elif is_spotify_playlist(decoded_query):
        result = process_playlist(decoded_query)
        return result

    else:
        return {"status": "error", "message": "invalid url"}


@app.get("/downloads/{filename}")
async def get_file(filename: str):
    file_path = f"downloads/{filename}"
    return FileResponse(path=file_path, filename=filename, media_type="application/zip")
