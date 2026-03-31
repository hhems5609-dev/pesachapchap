import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 1. Ensure the 'static' directory exists so Render doesn't throw a warning
if not os.path.exists("static"):
    os.makedirs("static")

# 2. Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index(request: Request):
    # Fixed the dictionary format for Jinja2
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/play")
async def play_video(request: Request):
    # Fixed the dictionary format for Jinja2
    return templates.TemplateResponse("play.html", {"request": request})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # We use app directly here for stability on Render
    uvicorn.run(app, host="0.0.0.0", port=port)

