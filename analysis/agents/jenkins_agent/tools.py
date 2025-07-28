from tracemalloc import start
from langchain_core.tools import tool
from langgraph.types import Command, Send

import re
from datetime import datetime, timezone
from typing import List, Optional, Union, Annotated
from langchain_core.messages import filter_messages
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import InjectedState
from .log_parser import parse_log_file


@tool
def get_logs(
    file_path: str,
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
    print("Getting logs from file: ", file_path)
    return parse_log_file(file_path, levels, start_time, end_time)


@tool(
    "validation_issue_analyzer",
    description="Transfer to the validation_issue_analyzer when the root cause is related to validation failure , assertion failure or verification failure",
)
def transfer_to_validation_issue_analyzer(
    state: Annotated[MessagesState, InjectedState],
) -> Command:
    ai_messages = filter_messages(state["messages"], include_types="ai")
    root_cause = ai_messages[-1].content[0]["text"]
    print(
        "state at tranfer tool ",
        filter_messages(state["messages"], include_types="ai")[-1],
    )
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
