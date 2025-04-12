from groq import Groq
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from uuid import uuid4
from datetime import datetime, UTC, timedelta, timezone
import random

from fastapi import Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from jose import JWTError, jwt

from pydantic import BaseModel, Field, conlist, conset
from enum import Enum
from datetime import datetime, date, timezone
from uuid import uuid4
from decimal import Decimal


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 60 minutes * 24 hours * 30 days -> 30 days
SECURITY: bool = False  # TODO: secure=False for local development

class Action(BaseModel):
    user_id: str | None
    ip_address: str | None
    action_code: str | None
    action: dict | None
    timestamp: datetime


system_message = "You are a business analyst who summarizes business articles. Please provide a summary of the article provided by user. Your output is the summary only, do not use prealbula like 'Here is a summary of the article:'"


# Actions

async def write_action(request: Request, user_id: str | None = None, ip_address: str | None = None, 
                       action_code: str | None = None, action: dict | None = None, actions_collection: str = "actions"):
    
    action = Action(
        user_id=user_id,
        ip_address=ip_address,
        action_code=action_code,
        action=action,
        timestamp=datetime.now(timezone.utc)
    )

    await request.app.mongodb[actions_collection].insert_one(action.model_dump())


# Client info

async def get_client_ip(request: Request, port_included: bool = False) -> str | None:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(':')[0]
        return ip_address if not port_included else x_forwarded_for
    return None


# Email

async def send_email(user_email: str, service_email: str, email_subject: str, email_html_content: str):
    message = Mail(
        from_email=service_email,
        to_emails=user_email,
        subject=email_subject,
        html_content=email_html_content)
    try:
        response = sg_client.send(message)
        return response.status_code
    
    except Exception as e:
        print('Error sending email:', e)


# Token functions

def create_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expires_delta = expires_delta if expires_delta else timedelta(minutes=15)
    # print('Expires delta:', expires_delta)

    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_access_token_for_user(user_id: str, scope: str = "tier_1"):
    data = dict(sub=user_id, scope=scope)
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return create_token(data=data, expires_delta=expires_delta)


def create_cookies_confirmed_token(cookies_confirmed: bool, scope: str = "tier_1"):
    data = dict(cookies_confirmed=cookies_confirmed, scope=scope)
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return create_token(data=data, expires_delta=expires_delta)


def set_token_to_browser(response: Response, token_name: str, token: str):
    response.set_cookie(
        key=token_name,
        value=token,
        secure=SECURITY,   
        httponly=True,
        samesite="lax")

    return response


def get_user_data_from_token(token: str):
    """
    Retrieves user data from a JWT token.

    Args:
        token (str): The JWT token containing user data.

    Returns:
        dict: A dictionary containing the user_id and is_guest extracted from the token.
              Returns None if the token is invalid or if the user data cannot be extracted.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return dict(user_id=payload.get("sub"))
    
    except JWTError:
        return None


def get_user_id_from_request(request: object) -> str | None:
    """
    Get user_id from token.

    Args:
        request (Request): The incoming request object.
        token (str): The token to get user_id from.

    Returns:
        str: The user_id from the token.
    """
    token: str = request.cookies.get("access_token") 
    user_data = get_user_data_from_token(token) if token else None
    user_id = user_data.get("user_id") if user_data else None

    return user_id


def is_cookies_confirmed(request: Request) -> bool:
    token = request.cookies.get("cookies")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cookies_confirmed = payload.get("cookies_confirmed")
    
    except Exception:
        cookies_confirmed = False
    
    return cookies_confirmed
