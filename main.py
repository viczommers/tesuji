import os
from dotenv import load_dotenv
from portia import (
    Config,
    LLMModel,
    LLMProvider,
    Portia,
    example_tool_registry,
)

load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')

# Create a default Portia config with LLM provider set to Azure OpenAI and model to GPT 4o
azure_config = Config.from_default(
    llm_provider=LLMProvider.AZURE_OPENAI,
    llm_model_name=LLMModel.AZURE_GPT_4_O,
    azure_openai_api_key=AZURE_OPENAI_API_KEY,
    azure_openai_endpoint=AZURE_OPENAI_ENDPOINT,
)
# Instantiate a Portia instance. Load it with the config and with the example tools.
portia = Portia(config=azure_config, tools=example_tool_registry)
# Run the test query and print the output!
plan_run = portia.run('add 1 + 2')
print(plan_run.model_dump_json(indent=2))