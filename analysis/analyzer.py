from langgraph.graph import StateGraph, START
from agents.jenkins_agent.agent import get_jenkins_agent
from agents.datadog_agent.agent import get_datadog_agent
from langgraph.graph.message import MessagesState


def jenkins_node(state):
    jenkins_log_analyzer_agent = get_jenkins_agent()
    response = jenkins_log_analyzer_agent.invoke(state)
    return {"messages": response["messages"]}


def validation_issue_analyzer_node(state):
    validation_issue_analyzer_agent = get_datadog_agent()
    response = validation_issue_analyzer_agent.invoke(state)
    return {"messages": response["messages"]}


def get_analyzer_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("jenkins_log_analyzer_agent", jenkins_node)
    builder.add_node("validation_issue_analyzer", validation_issue_analyzer_node)
    builder.add_edge(START, "jenkins_log_analyzer_agent")
    return builder.compile()


if __name__ == "__main__":
    analyzer = get_analyzer_graph()
    print("done")
