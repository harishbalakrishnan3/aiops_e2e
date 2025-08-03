from langchain_core.tools import tool
from langgraph.types import Command, Send

from typing import List, Optional, Union, Annotated
from langchain_core.messages import filter_messages
from langgraph.prebuilt import InjectedState
from .log_parser import parse_log_file
from model import AgentState
from data_proccesor.data_processor import processed_file_path


@tool
def get_logs(
    path: str,
    levels: Optional[Union[str, List[str]]] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> List[dict]:
    """Get related jenkins logs

    Args:
        file_path: path to the log file
        levels: optional field filters logs retreived by log level INFO , DEBUG , ERROR
        start_time: optional field to get logs with timestamp that is greater than start time
        end_time: optional field to get logs with timestamp that is less than end time
    Returns:
        List of log entries
    """
    path = processed_file_path / path
    print("Getting logs from file: ", processed_file_path / path)
    return parse_log_file(path, levels, start_time, end_time)


@tool(
    "validation_issue_analyzer",
    description="Transfer to the validation_issue_analyzer when the root cause is related to validation failure , assertion failure or verification failure",
)
def transfer_to_validation_issue_analyzer(
    state: Annotated[AgentState, InjectedState],
) -> Command:
    ai_messages = filter_messages(state["messages"], include_types="ai")
    root_cause = ai_messages[-1].content[0]["text"]
    agent_prompt = f"""
    Based on the high level root cause analysis . The following issues where discovered :
    {root_cause}

    Please analyze the issue further based on the given analysis and find the final root cause
    """
    task_description_message = {"role": "user", "content": agent_prompt}
    agent_input = {**state, "messages": [task_description_message]}
    return Command(
        goto=[Send("validation_issue_analyzer", agent_input)],
        graph=Command.PARENT,
    )
