from langgraph.graph import StateGraph, START, END
from agents.jenkins_agent.agent import get_jenkins_agent
from agents.datadog_agent.agent import get_datadog_agent
from model import AnalyzerState, AgentState
from langchain_core.messages import filter_messages
from langchain_core.messages import AIMessage


def get_analyzer_graph():
    builder = StateGraph(AnalyzerState)
    builder.add_node("jenkins_log_analyzer_agent", jenkins_node)
    builder.add_node("validation_issue_analyzer", validation_issue_analyzer_node)
    builder.add_node("analyzer_result_node", analyzer_result_node)
    builder.add_edge(START, "jenkins_log_analyzer_agent")
    builder.add_edge("jenkins_log_analyzer_agent", "analyzer_result_node")
    builder.add_edge("validation_issue_analyzer", "analyzer_result_node")
    builder.add_edge("analyzer_result_node", END)
    return builder.compile()


def jenkins_node(state: AnalyzerState):
    jenkins_log_analyzer_agent = get_jenkins_agent()
    response = jenkins_log_analyzer_agent.invoke(state)
    return {"messages": response["messages"]}


def validation_issue_analyzer_node(state: AgentState):
    # TODO ADD BACK FTER TESTING CONSOLIDATION OF RESULTS
    # validation_issue_analyzer_agent = get_datadog_agent()
    # response = validation_issue_analyzer_agent.invoke(state)
    return {"messages": [AIMessage(content="test response")]}


def analyzer_result_node(state: AnalyzerState):
    ai_messages = filter_messages(state["messages"], include_types="ai")
    if len(ai_messages) == 0:
        return {"task_analysis": []}
    return {"task_analysis": [ai_messages[-1].content]}
