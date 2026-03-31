import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# 1. Initialize FastAPI
app = FastAPI()

# 2. Safety Check: Create 'static' folder if it doesn't exist
# This prevents Render from crashing when trying to mount a missing folder
if not os.path.exists("static"):
    os.makedirs("static")

# 3. Setup Templates and Static Files
# directory="templates" assumes your .html files are in a folder named templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Routes
@app.get("/")
async def index(request: Request):
    """
    Renders the home page. 
    Crucial: Passing {"request": request} is required for FastAPI Jinja2 templates.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/play")
async def play_video(request: Request):
    """
    Renders the play page for Pesa ChapChap videos.
    """
    return templates.TemplateResponse("play.html", {"request": request})

# 5. Render-Specific Execution
if __name__ == "__main__":
    # Render assigns a port via environment variable. 
    # If not found (like in Termux), it defaults to 10000.
    port = int(os.environ.get("PORT", 10000))
    
    # We use the string "server:app" to allow for better hot-reloading/stability
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

