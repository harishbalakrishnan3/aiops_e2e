import os
from langgraph.graph import StateGraph, START, END
from agents.jenkins_agent.agent import get_jenkins_agent
from agents.datadog_agent.agent import get_datadog_agent
from langgraph.constants import Send
from data_proccesor.data_processor import processed_file_path
from model import AnalyzerState, Task, ParentState
from utils.utils import get_scenario_name_from_file, get_data_source_from_file


def jenkins_node(state: AnalyzerState):
    jenkins_log_analyzer_agent = get_jenkins_agent()
    response = jenkins_log_analyzer_agent.invoke(state)
    return {"messages": response["messages"]}


def validation_issue_analyzer_node(state: AnalyzerState):
    print("validation_issue_analyzer_node state", state)
    # TODO ADD BACK FTER TESTING CONSOLIDATION OF RESULTS
    # validation_issue_analyzer_agent = get_datadog_agent()
    # response = validation_issue_analyzer_agent.invoke(state)
    return {"messages": "test response"}


def get_analyzer_graph():
    builder = StateGraph(AnalyzerState)
    builder.add_node("jenkins_log_analyzer_agent", jenkins_node)
    builder.add_node("validation_issue_analyzer", validation_issue_analyzer_node)
    builder.add_edge(START, "jenkins_log_analyzer_agent")
    return builder.compile()


def task_creator(state):
    all_tasks = []
    for root, dirs, files in os.walk(processed_file_path):
        if len(files) != 0:
            all_tasks.extend(
                [
                    Task(
                        scenario_name=get_scenario_name_from_file(file),
                        data_source=get_data_source_from_file(file, root),
                        tenant_uid="your_tenant_uid",
                    )
                    for file in files
                    if file.startswith("scenario_")
                ]
            )
    return {"tasks": all_tasks}


def task_consolidator(state):
    print("state of consolidator ", state)
    return {"messages": "dummy state"}


def continue_to_analyzer(state: ParentState):
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


def final_graph():
    analyzer_subgraph = get_analyzer_graph()
    builder = StateGraph(ParentState)
    builder.add_node("TaskCreator", task_creator)
    builder.add_node("AnalyzerGraph", analyzer_subgraph)
    builder.add_node("ResultConsolidator", task_consolidator)
    builder.add_edge(START, "TaskCreator")
    builder.add_conditional_edges(
        "TaskCreator", continue_to_analyzer, ["AnalyzerGraph"]
    )
    builder.add_edge("AnalyzerGraph", "ResultConsolidator")
    builder.add_edge("ResultConsolidator", END)
    graph = builder.compile()
    return graph


if __name__ == "__main__":
    graph = final_graph()
    print(graph.invoke({"messages": "hello initial"}))
