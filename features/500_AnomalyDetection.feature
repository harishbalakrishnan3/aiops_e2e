Feature: Anomaly Detection Testing

  Background:
    Given the tenant onboard state is ONBOARD_SUCCESS

  Scenario: Test CONNECTIONS_ANOMALY for standalone device
    # Firing Test scenarios
    Then push timeseries for 60 minute(s) of which send last 10 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes  |noise |
      | conn_stats             | conn_stats=connection, description=in_use | 200         | 800       | 0                  | 60                      |false |
      | conn_stats             | conn_stats=xlate, description=in_use      | 200         | 800       | 0                  | 60                      |false |
      | conn_stats             | conn_stats=cps, description=tcp           | 200         | 800       | 0                  | 60                      |true |
      | conn_stats             | conn_stats=cps, description=udp           | 200         | 800       | 0                  | 60                      |false |
      | conn_stats_threshold   | type=upper                                | 100         | 700       | 0                  | 60                      |false |
      | conn_stats_threshold   | type=lower                                | 50          | 650        | 0                 | 60                      |false |
    Then verify if an CONNECTIONS_ANOMALY insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 | 
      | NAT Translations            | 
      | TCP Connections Rate        | 
      | UDP Connections Rate        |
    Then push timeseries for 2 minute(s) of which send last 3 minute(s) of timeseries in live mode
      | metric_name | label_values    | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | conn_stats             | conn_stats=connection, description=in_use | 800         | 900       | 0                  | 2                     |
      | conn_stats_threshold   | type=upper                                | 950         | 1000      | 0                  | 2                     |
      | conn_stats_threshold   | type=lower                                | 750         | 800       | 0                  | 2                     |
    Then verify if an CONNECTIONS_ANOMALY insight with state RESOLVED is created with a timeout of 10 minute(s)


  Scenario: Test CONNECTIONS_ANOMALY for HA device
    # Firing Test scenarios
    Then push timeseries for 60 minute(s) of which send last 10 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes  | noise |
      | conn_stats             | conn_stats=connection, description=in_use | 200         | 800       | 0                  | 60                      | true |
      | conn_stats             | conn_stats=xlate, description=in_use      | 200         | 800       | 0                  | 60                      | true |
      | conn_stats             | conn_stats=cps, description=tcp           | 200         | 800       | 0                  | 60                      | true |
      | conn_stats             | conn_stats=cps, description=udp           | 200         | 800       | 0                  | 60                      | true |
      | ftd_ha                 | ftd_ha=node_state                         | 1           | 1         | 0                  | 60                      | false |
      | conn_stats_threshold   | type=upper                                | 100         | 700       | 0                  | 60                      | true |
      | conn_stats_threshold   | type=lower                                | 50          | 650       | 0                  | 60                      | true |
    Then verify if an CONNECTIONS_ANOMALY insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then confirm correlated metrics
      | metric_name                 | 
      | NAT Translations            | 
      | TCP Connections Rate        | 
      | UDP Connections Rate        |
    Then push timeseries for 2 minute(s) of which send last 3 minute(s) of timeseries in live mode
      | metric_name | label_values    | start_value | end_value | start_spike_minute | spike_duration_minutes |
      | conn_stats             | conn_stats=connection, description=in_use | 800         | 900       | 0                  | 2                     |
      | conn_stats_threshold   | type=upper                                | 950         | 1000      | 0                  | 2                     |
      | conn_stats_threshold   | type=lower                                | 750         | 800       | 0                  | 2                     |
      | ftd_ha                 | ftd_ha=node_state                         | 1           | 1         | 0                  | 2                     |
    Then verify if an CONNECTIONS_ANOMALY insight with state RESOLVED is created with a timeout of 10 minute(s)