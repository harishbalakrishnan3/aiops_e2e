import os
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from data_proccesor.data_processor import processed_file_path
from model import Task, OrchestratorState
from utils.utils import (
    get_scenario_name_from_file,
    get_data_source_from_file,
    get_tenant_uid,
)
from .analyzer_graph import get_analyzer_graph


def get_orchestrator_graph():
    builder = StateGraph(OrchestratorState)
    builder.add_node("TaskCreator", task_creator)
    builder.add_node("AnalyzerGraph", get_analyzer_graph())
    builder.add_node("ResultConsolidator", task_consolidator)
    builder.add_edge(START, "TaskCreator")
    builder.add_conditional_edges(
        "TaskCreator", continue_to_analyzer, ["AnalyzerGraph"]
    )
    builder.add_edge("AnalyzerGraph", "ResultConsolidator")
    builder.add_edge("ResultConsolidator", END)
    graph = builder.compile()
    return graph


def task_creator(state: OrchestratorState):
    all_tasks = []
    for root, dirs, files in os.walk(processed_file_path):
        if len(files) != 0:
            all_tasks.extend(
                [
                    Task(
                        scenario_name=get_scenario_name_from_file(file),
                        data_source=get_data_source_from_file(file, root),
                        tenant_uid=get_tenant_uid(),
                    )
                    for file in files
                    if file.startswith("scenario_")
                ]
            )
    return {"tasks": all_tasks}


def task_consolidator(state):
    print("state of consolidator ", state)
    return {"result": state["task_analysis"]}


def continue_to_analyzer(state: OrchestratorState):
    print("continue to analyzer, state", state)
    return [
        Send(
            "AnalyzerGraph",
            {
                "messages": f"Some failure are detected in this scenario . this log file is {task['data_source']}",
                "tenant_uid": task["tenant_uid"],
                "scenario_name": task["scenario_name"],
            },
        )
        for task in state["tasks"]
    ]
