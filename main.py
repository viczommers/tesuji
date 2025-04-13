import pathlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from contextlib import asynccontextmanager
import aiohttp
import asyncio
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
