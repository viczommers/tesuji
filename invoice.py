
from dotenv import load_dotenv
from typing import Optional

from portia import (
    ActionClarification,
    InputClarification,
    MultipleChoiceClarification,
    PlanRunState,
    Portia,
    example_tool_registry,
    Config,
    StorageClass,
    LLMProvider
)
from pydantic import BaseModel,Field
from registry import custom_tool_registry
class AppointmentData(BaseModel):
    postcode: str
    insurance_company: str = Field(default="", description="This field is optional")
    specialty: str = Field(default="", description="This field is optional")
    procedure: str = Field(default="", description="This field is optional")
    diagnostic: str = Field(default="", description="This field is optional")
load_dotenv()

# complete_tool_registry = example_tool_registry + custom_tool_registry

data = AppointmentData(
    postcode = "NW1 8DU",
    insurance_company = "",
    specialty = "Cardiology",
    procedure = "FIT (Faecal Immunochemistry Test)",
    diagnostic = "Intrathecal neurolysis"
)

# class Patient(BaseModel):
#     full_name: str = ''
#     date_of_birth: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # TODO: YYYY-MM-DD
#     insurance_company: insurance_list | None = None
#     policy_number: str | None = None
#     pre_authorisation: str 
#     address: str = '' # TODO: breakdown address into street, city, state, zip, country
#     diagnostic_list: list[diagnostic_codes]
#     diagnostic_descriptions: list[str] | None = None # TODO: index match from diagnostic_codes
#     diagnostic_total_charge: int | 0 = 0 #positive intereger
#     # lead_practicioner_provider_number: str | None = None # either gmc_number or provider_number is required
#     # lead_practicioner_gmc_number: int | None = None # either gmc_number or provider_number is required

# class Treatment(BaseModel):
#     care_type: Literal['inpatient', 'outpatient', 'daycase', 'other'] = 'outpatient'
#     date_of_treatment: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # TODO: YYYY-MM-DD should be at least today & not later than 6 month from today
#     procedure_list: list[procedure_codes]
#     procedure_description: str | None = None # TODO: index match from procedure_codes
#     treatment_total_charge: int | 0 = 0 #positive intereger

# class Claim(BaseModel):
#     invoice: Invoice
#     practicioner: Practicioner
#     insurer: #TODO: 
#     due_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) 
#     status: Literal['issued','validated','failed','authorised','declined','review']

# class Invoice(BaseModel):
#     patient: Patient
#     # practicioner: Practicioner
#     treatment: Treatment | None = None
#     total_charge: int =  #TODO: sum treatment_total_charge and diganostics_total_charge if not None
#     currency: Literal['EUR', 'GBP', 'USD'] = 'USD'


# Instantiate a Portia instance. Load it with the default config and with Portia cloud tools above
portia = Portia(config=Config(storage_class=StorageClass.DISK,
                              storage_dir="./logging_dump",
                              llm_provider=LLMProvider.AZURE_OPENAI,
                              default_log_sink="output.txt",
                              azure_openai_api_key="9nJVn32m8BdX6MzQQUljGD3P14uYdSHujzaXYz9i4CXn6duklDPCJQQJ99BDACYeBjFXJ3w3AAAAACOGN3bw",
                              azure_openai_endpoint="https://encode-hackathon-secret.cognitiveservices.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview",
                    )
                )

# Generate the plan from the user query and print it
prompt = (
    f"Check if procedure{data.diagnostic} is whinin specialist compenecy of doctor who practices {data.specialty}. If chronic, raise a clarification before proceeding."
    f"Check if the treatment {data.procedure} and diagnostic test {data.diagnostic} imply a chronic condition or acute presentation. If chronic, raise a clarification before proceeding."
)


plan = portia.plan(prompt)
#print(f"{plan.model_dump_json(indent=2)}")
# Run the plan
print(f"Running plan {plan.id}")
plan_run = portia.run_plan(plan)

while plan_run.state == PlanRunState.NEED_CLARIFICATION:
    # If clarifications are needed, resolve them before resuming the plan run
    for clarification in plan_run.get_outstanding_clarifications():
        # Usual handling of Input and Multiple Choice clarifications
        if isinstance(clarification, (InputClarification, MultipleChoiceClarification)):
            print(f"{clarification.user_guidance}")
            user_input = input("Please enter a value:\n" 
                            + (("\n".join(clarification.options) + "\n") if "options" in clarification else ""))
            plan_run = portia.resolve_clarification(clarification, user_input, plan_run)
        
        # Handling of Action clarifications
        if isinstance(clarification, ActionClarification):
            print(f"{clarification.user_guidance} -- Please click on the link below to proceed.")
            print(clarification.action_url)
            plan_run = portia.wait_for_ready(plan_run)

    # Once clarifications are resolved, resume the plan run
    plan_run = portia.resume(plan_run)
    

# Serialise into JSON and print the output
#print(f"{plan_run.model_dump_json(indent=2)}")

# final_output = plan_run.outputs.final_output.get_value()
# print(final_output)
# return final_output