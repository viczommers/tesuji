from pydantic import BaseModel, Field, conlist, conset
from enum import Enum
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from decimal import Decimal
from typing import Literal
from bson import Decimal128

insurance_list = Literal['BUPA', 'AXA', 'OTHER']
diagnostic_codes = Literal['ICD-10', 'ICD-9', 'OTHER']
procedure_codes = Literal['CPT', 'OTHER']

pre_authoristion_dict = [
    {'1234567890': 'BUPA',}
    'AXA': 'AXA',
    'OTHER': 'OTHER'
]

class Patient(BaseModel):
    full_name: str = ''
    date_of_birth: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # TODO: YYYY-MM-DD
    insurance_company: insurance_list | None = None
    policy_number: str | None = None
    pre_authorisation: str 
    address: str = '' # TODO: breakdown address into street, city, state, zip, country
    diagnostic_list: list[diagnostic_codes]
    diagnostic_descriptions: list[str] | None = None # TODO: index match from diagnostic_codes
    diagnostic_total_charge: int | 0 = 0 #positive intereger
    # lead_practicioner_provider_number: str | None = None # either gmc_number or provider_number is required
    # lead_practicioner_gmc_number: int | None = None # either gmc_number or provider_number is required

class Treatment(BaseModel):
    care_type: Literal['inpatient', 'outpatient', 'daycase', 'other'] = 'outpatient'
    date_of_treatment: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # TODO: YYYY-MM-DD should be at least today & not later than 6 month from today
    procedure_list: list[procedure_codes]
    procedure_description: str | None = None # TODO: index match from procedure_codes
    treatment_total_charge: int | 0 = 0 #positive intereger

class Claim(BaseModel):
    invoice: Invoice
    practicioner: Practicioner
    insurer: #TODO: 
    due_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) 
    status: Literal['issued','validated','failed','authorised','declined','review']

class Invoice(BaseModel):
    patient: Patient
    # practicioner: Practicioner
    treatment: Treatment | None = None
    total_charge: int =  #TODO: sum treatment_total_charge and diganostics_total_charge if not None
    currency: Literal['EUR', 'GBP', 'USD'] = 'USD'

class Agent(BaseMode):


class SeniorAgent(BaseModel):
    escalatiom 
    triage 
    issue_type: Literal['admin','criitical','other']
    invoke_human_break: bool = false


class Human(BaseModel):
    override: bool = false