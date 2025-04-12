from pydantic import BaseModel, Field, conlist, conset
from enum import Enum
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from decimal import Decimal
from typing import Literal
from bson import Decimal128

class Money(BaseModel):
    amount: Decimal128
    currency: Literal['£', '€', '$'] = '$'
 
    class Config:
        arbitrary_types_allowed = True
 
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_decimal128
 
    @classmethod
    def validate_decimal128(cls, v):
        if isinstance(v, Decimal128):
            return v
        return Decimal128(str(v))


class ViewPoint(BaseModel):
    viewpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    text_on_checkbox: str
    viewpoint: str  # Viewpoint discritption for LLM


class ViewPointsList(BaseModel):
    list_id: str = Field(default_factory=lambda: str(uuid4()))
    viewpoints: list[ViewPoint]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UploadStatus(str, Enum):
    uploaded = 'uploaded'
    screenshots_confirmed = 'screenshots_confirmed'
    screenshots_processed = 'screenshots_processed'
    screenshots_cancelled = 'screenshots_cancelled'
    suggested_queries_generated = 'suggested_queries_generated'
    query_submitted = 'query_submitted'
    query_processed = 'query_processed'


class UploadedFile(BaseModel):
    file_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    size: int
    type: str
    download_url: str = ''
    is_deleted: bool = False


class Query(BaseModel):
    query: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    economy: str | None = None
    keywords: list[str] | None = None
    vectors: list[list[float]] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: list[dict] = []  # list of chunks as the response of LLM
    summary: str = ''  # Summary of the result
    tool_calls: list = []
    is_suggested_query: bool = True


class DrillDown(Query):
    drilldown_id: str = Field(default_factory=lambda: str(uuid4()))  # link to this drilldown ==> .../drilldown/{drilldown_id}
    user_id: str | None = None  # User who created this drilldown (None for anonymous user)


class Report(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None
    query: Query 
    report: list[dict] = [] # Report data


class Upload(BaseModel):  #TODO: add suggested queries
    upload_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    files: list[UploadedFile] = []
    selected_viewpoints: list[ViewPoint] = [] # Viewpoints
    suggested_queries: list[Query] = []  # Suggested queries based on uploaded screenshots and/or enetered text query
    initial_query: str | None = None
    user_query: Query | None = None  # queries: list[Query] = []
    drill_downs: list[DrillDown] = []
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reports: list[Report] = []
    status: UploadStatus | str = UploadStatus.uploaded.value

# www.abc.com/query/83829832002302

class UserInterface(BaseModel):
    interface_id: str = Field(default_factory=lambda: str(uuid4()))
    info_text: str = 'Build & validate your own macro prediction themes with AI Agents'
    screenshots_upload_title: str = 'Choose screenshots to upload (e.g. Favourite Chart, Watchlist, News Article)'
    text_query_title: str = 'and/or enter your query directly to begin exploring'
    rotating_placeholders: list[str] = ['Key Shifts in FOMC Expectations Since the Last Meeting',
                                        'How recent U.S. payroll reports have influenced NASDAQ 100 index performance?',
                                        'Recent Updates of Euro Area Consumer Confidence and Borrowing Trends',
                                        'Have defaults or recession expectations risen?',
                                        'Latest surprise in the US unemployment rates, job openings, or labor force participation',
                                        'How changes in the PCE risks impact QQQ stock price movementum?',
                                        'US Treasury’s Latest Quarterly Refunding Strategy and Its Impact on Short-Term Yields',
                                        ]
    rotating_time: int = 5  # Time in seconds


class AuthLink(BaseModel):
    auth_link: str = Field(default_factory=lambda: str(uuid4()))
    expires_at: datetime = datetime.now(timezone.utc) + timedelta(minutes=10)  #TODO: set to 10 minutes in production
    access_token_assigned: bool = False  # Only one acces_token per auth_link (for one user's browser)


class Transaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    amount: Money
    description: str  # query 746648be-bcf6-4dae-9342-f7968bd6aaf4
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    linkedin_profile: str | None = None
    linkedin_profile_image_url: str | None = None
    full_name: str | None = None
    user_interface: UserInterface
    view_points_list: str  # id of viewpoints list to show to user based on his profile and investment intents
    uploads: list[str] = []  # List of upload ids
   
    drill_down_allowed: bool = True
    # balance: Money = Money(amount=Decimal128('500.00'))
    query_price: Money = Money(amount=Decimal128('5.00'))

    cookies_confirmed: bool = False
    auth_links: list[AuthLink] = []
    is_active: bool = True
    timestamps: dict = {'created_at': datetime.now(timezone.utc), 'last_login': datetime.now(timezone.utc), 'updated_at': datetime.now(timezone.utc)}

