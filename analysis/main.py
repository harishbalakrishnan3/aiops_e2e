from graphs.orchestrator_graph import get_orchestrator_graph

if __name__ == "__main__":
    graph = get_orchestrator_graph()
    print(graph.invoke({"messages": "hello initial"}))
