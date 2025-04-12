
from portia import InMemoryToolRegistry

from phin_tool import PhinTool

custom_tool_registry = InMemoryToolRegistry.from_local_tools(
    [
        PhinTool(),
    ],
)
    