from typing_extensions import TypedDict
from typing_extensions import Annotated, Optional
from langgraph.graph.message import add_messages
import operator
from langgraph.prebuilt.chat_agent_executor import AgentState


class Task(TypedDict):
    scenario_name: str
    data_source: str
    tenant_uid: str


class ParentState(AgentState):
    messages: Annotated[list, add_messages]
    result: Annotated[list, operator.add]
    tasks: list[Task]


class AnalyzerState(AgentState):
    messages: Annotated[list, add_messages]
    tenant_uid: Optional[str]
    scenario_name: Optional[str]
