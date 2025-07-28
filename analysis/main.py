from analyzer import get_analyzer_graph
from langchain_core.messages import (
    HumanMessage,
)

if __name__ == "__main__":
    analyzer = get_analyzer_graph()
    # validation issue
    anomaly_log_file = "./mock_data/analysis/processed/Anomaly/scenario_Testing_Anomaly_Detection_for_Connection_Stats_With_Simple_Linear_Spike.txt"
    #setup issue
    correlation_log_file = "./mock_data/analysis/processed/Correlation/scenario_Push_data_and_test_multi_correlation_alerts_for_CLUSTER_control_device.txt"


    final_state = analyzer.invoke(
        {"messages": [HumanMessage(content=f"Some failure are detected in this scenario . this log file is {anomaly_log_file}")]},
        # config={"configurable": {"thread_id": 42}}
    )

        