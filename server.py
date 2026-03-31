import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# 1. Initialize FastAPI
app = FastAPI()

# 2. Setup Templates and Static Files
# Make sure you have a folder named 'templates' and 'static' in your root directory
templates = Jinja2Templates(directory="templates")

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"Warning: Static directory not found: {e}")

# 3. Routes
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/play")
async def play_video(request: Request):
    # This renders your new play.html template
    return templates.TemplateResponse("play.html", {"request": request})

# 4. Render-Specific Startup
if __name__ == "__main__":
    # Render assigns a port dynamically. We MUST use os.environ.get
    # Defaulting to 10000 is standard for Render
    port = int(os.environ.get("PORT", 10000))
    
    # We bind to 0.0.0.0 so the outside world can reach the container
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

