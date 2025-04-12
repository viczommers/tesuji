
from dotenv import load_dotenv
from typing import Optional

from portia import (
    ActionClarification,
    InputClarification,
    MultipleChoiceClarification,
    PlanRunState,
    Portia,
    example_tool_registry,
)
from pydantic import BaseModel,Field
from registry import custom_tool_registry
class AppointmentData(BaseModel):
    postcode: str
    insurance_company: str = Field(default="", description="This field is optional")
    specialty: str = Field(default="", description="This field is optional")
    procedure: str = Field(default="", description="This field is optional")

load_dotenv()

complete_tool_registry = example_tool_registry + custom_tool_registry

data = AppointmentData(
    postcode = "NW1 8DU",
    insurance_company = "",
    specialty = "Cardiology",
    procedure = ""
)

# Instantiate a Portia instance. Load it with the default config and with Portia cloud tools above
portia = Portia(tools=complete_tool_registry)

# Generate the plan from the user query and print it
prompt = (
    f"Use PhinTool to navigate to the website and fill in the fields with mandatory field postcode with {data.postcode}, and optional fields following with {data.specialty} and {data.procedure}"
    f"Return a list of potential doctors and with the extracted fields distance, rating, consultation price and specialty that are a list of string. Ensure consultation price is low"
    f"Suggest one suitable doctor for the user and include a brief justification"
)
plan = portia.plan(prompt)
print(f"{plan.model_dump_json(indent=2)}")

# Run the plan
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
print(f"{plan_run.model_dump_json(indent=2)}")