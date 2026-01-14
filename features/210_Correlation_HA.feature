Feature: Correlation testing for HA devices
  Background: 
    Given the tenant onboard state is ONBOARD_SUCCESS
  # This feature tests correlation alerts specifically for HA (High Availability) device configurations
  
  Scenario: Push data and test multi correlation alerts for HA active device
    Then push timeseries for 60 minute(s) of which send last 6 minute(s) of timeseries in live mode
      | metric_name            | label_values                                     | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | cpu                    | cpu=lina_dp_avg                                  | 5           | 85        | 1                  | 55                     |
      | cpu                    | cpu=snort_avg                                    | 5           | 85        | 1                  | 55                     |
      | cpu                    | cpu=lina_cp_avg                                  | 12          | 90        | 1                  | 55                     |
      | mem                    | mem=used_percentage_lina                         | 5           | 85        | 1                  | 55                     |
      | mem                    | mem=used_percentage_snort                        | 5           | 85        | 1                  | 55                     |
      | conn_stats             | conn_stats=connection, description=in_use        | 12          | 90        | 1                  | 55                     |
      | interface              | description=input_bytes , interface=all          | 12          | 12        | 1                  | 55                     |
      | interface              | description=input_packets, interface=all         | 12          | 90        | 1                  | 55                     |
      | interface              | description=input_avg_packet_size, interface=all | 12          | 90        | 1                  | 55                     |
      | interface              | description=drop_packets                         | 12          | 90        | 1                  | 55                     |
      | deployed_configuration | deployed_configuration=number_of_ACEs            | 12          | 90        | 1                  | 55                     |
      | snort                  | description=denied_flow_events, snort=stats      | 12          | 90        | 1                  | 55                     |
      | snort3_perfstats       | snort3_perfstats=concurrent_elephant_flows       | 12          | 90        | 1                  | 55                     |
      | asp_drops              | asp_drops=snort-busy-not-fp                      | 12          | 90        | 1                  | 55                     |
    Then verify if an CPU_LINA_THRESHOLD_BREACH insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 |
      | Control Plane CPU           |
      | Connections                 |
      | Deployed ACE Configurations |
    Then verify if an CPU_SNORT_THRESHOLD_BREACH insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 |
      | Snort Denied Flows          |
      | Connections                 |
      | Control Plane CPU           |
    Then verify if an MEMORY_LINA_THRESHOLD_BREACH insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 |
      | Connections                 |
      | Deployed ACE Configurations |
    Then verify if an MEMORY_SNORT_THRESHOLD_BREACH insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 |
      | Connections                 |
    Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
      | metric_name | label_values                  | start_value | end_value | start_spike_minute  | spike_duration_minutes |
      | cpu         | cpu=lina_dp_avg               | 60          | 60        | 0                   | 1                      |
      | cpu         | cpu=snort_avg                 | 60          | 60        | 0                   | 1                      |
      | mem         | mem=used_percentage_lina      | 60          | 60        | 0                   | 1                      |
      | mem         | mem=used_percentage_snort     | 60          | 60        | 0                   | 1                      |
    Then verify if an CPU_LINA_THRESHOLD_BREACH insight with state RESOLVED is created with a timeout of 10 minute(s)
