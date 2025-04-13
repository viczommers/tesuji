import pathlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from contextlib import asynccontextmanager
import aiohttp
import asyncio
import uvicorn
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel

from test import book_appointment

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Simple in-memory storage for user searches
user_choices = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create aiohttp session
    app.aiohttp_session = aiohttp.ClientSession()
    yield
    await app.aiohttp_session.close()



async def stream_logs():
    print("Streaming logs...")
    log_dir = BASE_DIR / "logging_dump"
    
    if not log_dir.is_dir():
        yield f"data: The directory {log_dir} does not exist.\n\n"
        return  # Exit if the directory does not exist
    
    # Get all JSON files in the directory that start with "prun"
    json_files = list(log_dir.glob("prun*.json"))
    
    if not json_files:
        yield "data: No JSON files found."
        return  # Return if no files are found

    for json_file in json_files:
        print(f"Processing file: {json_file}")
        try:
            with open(json_file) as f:
                data = json.load(f)
                
                # Check if data is a list and handle accordingly
                if isinstance(data, list):
                    for item in data:
                        yield f"data: ID: {item.get('id')}, Plan ID: {item.get('plan_id')}, State: {item.get('state')}"
                        outputs = item.get('outputs', {})
                        if outputs:
                            for key, value in outputs.items():
                                yield f"data: {key}: {value.get('value')}\n\n"
                        else:
                            yield "data: No outputs found in this file.\n\n"
                else:
                    # If data is not a list, handle it as a single object
                    yield f"data: ID: {data.get('id')}, Plan ID: {data.get('plan_id')}, State: {data.get('state')}"
                    outputs = data.get('outputs', {})
                    if outputs:
                        for key, value in outputs.items():
                            yield f"data: {key}: {value.get('value')}"
                    else:
                        yield "data: No outputs found in this file."
        except json.JSONDecodeError as e:
            yield f"data: Error decoding JSON from file {json_file}: {e}"
        except Exception as e:
            yield f"data: An error occurred while processing {json_file}: {e}"

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint that redirects to the landing page"""
    return RedirectResponse(url="/landing")

@app.get("/landing", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Render the landing page with user details form"""
    return templates.TemplateResponse(
        "landing.html",
        {"request": request}
    )

@app.post("/search")
async def search_results(
    request: Request,
    postcode: str = Form(...),
    specialty: str = Form(...),
    insurance_company: str | None = Form(None),
    procedure: str | None = Form(None)
):
    """Handle the search request and show results"""
    # Store user details in session/memory for potential later use
    session_id = str(uuid4())
    user_choices[session_id] = {
        "postcode": postcode,
        "insurance_company": insurance_company,
        "specialty": specialty,
        "procedure": procedure,
        "timestamp": datetime.now(timezone.utc)
    }

    # Dummy search function that simulates processing time
    async def perform_dummy_search(postcode: str, specialty: str) -> dict:
        await asyncio.sleep(2)  # Simulate processing time
        dummy_output = book_appointment()
        return {
            "matches_found": 3,
            "potential_risks": ["Risk A", "Risk B"],
            "score": 85.5,
            "session_id": session_id,
            "booking_slot": dummy_output
        }
    
    # Perform the search
    search_results = await perform_dummy_search(postcode, specialty)
    
    response = templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "postcode": postcode,
            "insurance_company": insurance_company,
            "specialty": specialty,
            "procedure": procedure,
            "results": search_results
        }
    )
    
    # Set session cookie
    response.set_cookie(key="session_id", value=session_id, max_age=3600)
    return response

@app.get("/stream-logs")
async def stream_logs_endpoint():
    return EventSourceResponse(stream_logs())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
