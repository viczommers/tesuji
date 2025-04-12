
from dotenv import load_dotenv

from portia import (
    ActionClarification,
    InputClarification,
    MultipleChoiceClarification,
    PlanRunState,
    Portia,
    PortiaToolRegistry,
    default_config,
)

class FormData(BaseModel):
    postcode: str
    insurance_company: str
    specialty: str
    procedure: str

from browser_tool import BrowserTool
from portia.open_source_tools.search_tool import SearchTool
load_dotenv()


# Instantiate a Portia instance. Load it with the default config and with Portia cloud tools above
portia = Portia(tools=[SearchTool(),BrowserTool(infrastructure_option="local")])

# Generate the plan from the user query and print it
plan = portia.plan('Find the PHIN UK homepage url and give me a summary')
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