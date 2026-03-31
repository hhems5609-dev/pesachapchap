import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Create static dir if missing to stop the warning
if not os.path.exists("static"):
    os.makedirs("static")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index(request: Request):
    # Fixed for FastAPI
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/play")
async def play_video(request: Request):
    # Fixed for FastAPI
    return templates.TemplateResponse("play.html", {"request": request})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
