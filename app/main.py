from fastapi import FastAPI, Query, HTTPException
from app.downloader import process_song

app = FastAPI()

@app.get("/")
def root():
    return{"message:" : "Downloader is running"}

@app.get("/download")
def download_song(query: str = Query(..., description="spotify link")):
    if not query.startswith("https://open.spotify.com/"):
        raise HTTPException(status_code=400, detail="link not valid")

    result = process_song(query)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result