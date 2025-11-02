import os
from glob import glob
from time import sleep
from threading import Thread
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from fetch import fetch_races
from generate import generate_pages


GENERATED_DIR = "generated"
DEFAULT_PAGE = "Week.html"

FETCHING = True
LAST_UPDATE = None
RUNNING = True


def fetch_and_generate():
    global FETCHING, LAST_UPDATE
    FETCHING = True

    fetch_races()

    files = glob(f"{GENERATED_DIR}/*.html")
    for f in files:
        os.remove(f)

    generate_pages()

    LAST_UPDATE = datetime.now()
    FETCHING = False


def update_loop():
    count = 600
    while RUNNING:
        # sleep for 10 minutes before checking again
        if count >= 600:
            today = datetime.now()
            mon_at_two = today.weekday() == 0 and today.hour == 2
            already_run = LAST_UPDATE and today - LAST_UPDATE < timedelta(hours=1)

            # on first run or Monday at about 2
            if LAST_UPDATE is None or (mon_at_two and not already_run):
                fetch_and_generate()

            count = 0
        else:
            count += 1
        
        sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global RUNNING

    # schedule a data update once per week
    t = Thread(target=update_loop)
    t.start()

    yield

    RUNNING = False


# create an instance of FastAPI
app = FastAPI(lifespan=lifespan)

# serve the index, builds each page from query parameters
@app.get("/", response_class=FileResponse)
async def index():
    return f"{GENERATED_DIR}/{DEFAULT_PAGE}"

@app.get("/index.html", response_class=FileResponse)
async def index_html():
    return f"{GENERATED_DIR}/{DEFAULT_PAGE}"

@app.get("/style.css", response_class=FileResponse)
async def styles():
    return "style.css"

@app.get("/script.js", response_class=FileResponse)
async def styles():
    return "script.js"

@app.get("/{file_path:path}.html", response_class=FileResponse)
async def assets(file_path):
    if FETCHING:
        return "fetching.html"

    return f"{GENERATED_DIR}/{file_path}.html"


