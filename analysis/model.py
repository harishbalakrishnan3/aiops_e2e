from typing_extensions import TypedDict
from typing_extensions import Annotated, Optional
from langgraph.graph.message import add_messages
import operator
from langgraph.prebuilt.chat_agent_executor import AgentState


class Task(TypedDict):
    scenario_name: str
    data_source: str
    tenant_uid: str


class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    tasks: list[Task]
    # shared state filed between shared and parent graph , used for data passing between the graphs
    task_analysis: Annotated[list, operator.add]
    # result state field where the consolidated results are stored
    result: list


class AnalyzerState(TypedDict):
    messages: Annotated[list, add_messages]
    tenant_uid: Optional[str]
    scenario_name: Optional[str]
    # shared state filed
    task_analysis: Annotated[list, operator.add]


class AnalyzerAgentState(AgentState):
    messages: Annotated[list, add_messages]
    tenant_uid: Optional[str]
    scenario_name: Optional[str]
