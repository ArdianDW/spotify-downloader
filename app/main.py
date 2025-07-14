from fastapi import FastAPI, Query
from app.downloader import process_song

app = FastAPI()

@app.get("/")
def root():
    return{"message:" : "Downloader is running"}

@app.get("/download")
def download_song(query: str = Query(..., description="Judul lagu atau artist - title")):
    result = process_song(query)
    return result