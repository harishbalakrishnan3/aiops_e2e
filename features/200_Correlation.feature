Feature: Correlation testing
  # This feature tests if the desired alerts are raised for various correlation scenarios
  # Firing Test scenarios
  Scenario: Push data and test correlation alerts for CPU_LINA_THRESHOLD_BREACH
    Given the insights are cleared
    Then push timeseries for next 60 minutes of which send last 6 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | cpu                    | cpu=lina_dp_avg                           | 5           | 85        | 1                  | 55                     |
      | cpu                    | cpu=lina_cp_avg                           | 12          | 90        | 1                  | 55                     |
      | conn_stats             | conn_stats=connection, description=in_use | 12          | 90        | 1                  | 55                     |
      | interface              | description=input_bytes , interface=all   | 12          | 12        | 1                  | 55                     |
      | interface              | description=input_packets, interface=all  | 12          | 90        | 1                  | 55                     |
      | deployed_configuration | deployed_configuration=number_of_ACEs     | 12          | 90        | 1                  | 55                     |
    Then keep checking for 10 minute(s) if an CPU_LINA_THRESHOLD_BREACH insight with state ACTIVE is created
    Then push timeseries for next 2 minutes of which send last 2 minute(s) of timeseries in live mode
      | metric_name | label_values    | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | cpu         | cpu=lina_dp_avg | 60          | 60        | 0                  | 1                      |
    Then keep checking for 10 minute(s) if an CPU_LINA_THRESHOLD_BREACH insight with state RESOLVED is created

  Scenario: Push data and test correlation alerts for CPU_SNORT_THRESHOLD_BREACH
    Given the insights are cleared
    Then push timeseries for next 60 minutes of which send last 6 minute(s) of timeseries in live mode
      | metric_name | label_values                                     | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | cpu         | cpu=snort_avg                                    | 5           | 85        | 1                  | 55                     |
      | cpu         | cpu=lina_cp_avg                                  | 60          | 90        | 1                  | 55                     |
      | conn_stats  | conn_stats=connection, description=in_use        | 12          | 90        | 1                  | 55                     |
      | interface   | description=input_bytes , interface=all          | 12          | 12        | 1                  | 55                     |
      | interface   | description=input_packets, interface=all         | 12          | 90        | 1                  | 55                     |
      | interface   | description=input_avg_packet_size, interface=all | 12          | 90        | 1                  | 55                     |
      | snort       | description=denied_flow_events, snort=stats      | 12          | 90        | 1                  | 55                     |
    Then keep checking for 10 minute(s) if an CPU_SNORT_THRESHOLD_BREACH insight with state ACTIVE is created
    Then push timeseries for next 2 minutes of which send last 2 minute(s) of timeseries in live mode
      | metric_name | label_values  | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | cpu         | cpu=snort_avg | 60          | 60        | 0                  | 1                      |
    Then keep checking for 10 minute(s) if an CPU_SNORT_THRESHOLD_BREACH insight with state RESOLVED is created

  Scenario: Push data and test correlation alerts for MEMORY_LINA_THRESHOLD_BREACH
    Given the insights are cleared
    Then push timeseries for next 60 minutes of which send last 6 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | mem                    | mem=used_percentage_lina                  | 5           | 85        | 1                  | 55                     |
      | conn_stats             | conn_stats=connection, description=in_use | 12          | 90        | 1                  | 55                     |
      | interface              | description=input_bytes , interface=all   | 12          | 12        | 1                  | 55                     |
      | interface              | description=input_packets, interface=all  | 12          | 90        | 1                  | 55                     |
      | deployed_configuration | deployed_configuration=number_of_ACEs     | 12          | 90        | 1                  | 55                     |
    Then keep checking for 10 minute(s) if an MEMORY_LINA_THRESHOLD_BREACH insight with state ACTIVE is created
    Then push timeseries for next 2 minutes of which send last 2 minute(s) of timeseries in live mode
      | metric_name | label_values             | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | mem         | mem=used_percentage_lina | 60          | 60        | 0                  | 1                      |
    Then keep checking for 10 minute(s) if an MEMORY_LINA_THRESHOLD_BREACH insight with state RESOLVED is created

  Scenario: Push data and test correlation alerts for MEMORY_SNORT_THRESHOLD_BREACH
    Given the insights are cleared
    Then push timeseries for next 60 minutes of which send last 6 minute(s) of timeseries in live mode
      | metric_name | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | mem         | mem=used_percentage_snort                 | 5           | 85        | 1                  | 55                     |
      | conn_stats  | conn_stats=connection, description=in_use | 12          | 90        | 1                  | 55                     |
      | interface   | description=input_bytes , interface=all   | 12          | 12        | 1                  | 55                     |
      | interface   | description=input_packets, interface=all  | 12          | 90        | 1                  | 55                     |
    Then keep checking for 10 minute(s) if an MEMORY_SNORT_THRESHOLD_BREACH insight with state ACTIVE is created
    Then push timeseries for next 2 minutes of which send last 2 minute(s) of timeseries in live mode
      | metric_name | label_values              | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | mem         | mem=used_percentage_snort | 60          | 60        | 0                  | 1                      |
    Then keep checking for 10 minute(s) if an MEMORY_SNORT_THRESHOLD_BREACH insight with state RESOLVED is created