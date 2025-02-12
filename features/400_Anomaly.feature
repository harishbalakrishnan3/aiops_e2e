Feature: Testing Anomaly Detection
  Scenario: Testing Anomaly Detection for Connection Stats With Simple Linear Spike
    Given the tenant onboard state is ONBOARDED
    Then backfill metrics for a suitable device over 792 hour(s)
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes | seasonality_period_hours |
      | conn_stats             | conn_stats=connection, description=in_use | 15          | 200       | 0                  | 47520                  | 6                        |
    Then keep checking if conn_stats_threshold upper and lower bounds are ingested for 120 minute(s)
    # There will be a break in data here (aprox 2hrs) while it backfills
    Then push timeseries for 120 minute(s) of which send last 10 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes  |
      | conn_stats             | conn_stats=connection, description=in_use | 200         | 800       | 0                  | 110                     |
      | conn_stats             | conn_stats=xlate, description=in_use      | 200         | 800       | 0                  | 110                     |
      | conn_stats             | conn_stats=cps, description=tcp           | 200         | 800       | 0                  | 110                     |
      | conn_stats             | conn_stats=cps, description=udp           | 200         | 800       | 0                  | 110                     |
    Then verify if an CONNECTIONS_ANOMALY insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes  
      | conn_stats             | conn_stats=connection, description=in_use | 800         | 200       | 0                  | 1                     |
      | conn_stats             | conn_stats=xlate, description=in_use      | 800         | 200       | 0                  | 1                     |
      | conn_stats             | conn_stats=cps, description=tcp           | 800         | 200       | 0                  | 1                     |
      | conn_stats             | conn_stats=cps, description=udp           | 800         | 200       | 0                  | 1                     |
    Then verify if an CONNECTIONS_ANOMALY insight with state RESOLVED is created with a timeout of 10 minute(s)

    
  Scenario: Testing Anomaly Detection for Throughput Stats With Simple Linear Spike
    Given the tenant onboard state is ONBOARDED
    Then backfill metrics for a suitable device over 792 hour(s)
      | metric_name            | label_values                              | metric_type        |   start_value | end_value | start_spike_minute       | spike_duration_minutes     | seasonality_period_hours   | 
      | interface              | interface=all, description=input_bytes    | counter            |   55500          | 106500       | 0                  | 47520                      | 12                         |
      | interface              | interface=all, description=output_bytes   | counter            |   55500          | 106500       | 0                  | 47520                      | 12                         |
    Then keep checking if interface_threshold upper and lower bounds are ingested for 120 minute(s)
    # There will be a break in data here (aprox 2hrs) while it backfills
    Then push timeseries for 120 minute(s) of which send last 10 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | metric_type        |   start_value       | end_value     | start_spike_minute | spike_duration_minutes   |
      | interface              | interface=all, description=input_bytes    | counter            |   106500            |  606500       | 0                  | 110                      |
      | interface              | interface=all, description=output_bytes   | counter            |   106500            |  606500       | 0                  | 110                      |
    Then verify if an THROUGHPUT_ANOMALY insight with state ACTIVE is created with a timeout of 10 minute(s)
    Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
      | metric_name            | label_values                              | metric_type        |   start_value       | end_value     | start_spike_minute | spike_duration_minutes   |
      | interface              | interface=all, description=input_bytes    | counter            |   106500            |  221650       | 0                  | 1                        |
      | interface              | interface=all, description=output_bytes   | counter            |   106500            |  221650       | 0                  | 1                        |
    Then verify if an THROUGHPUT_ANOMALY insight with state RESOLVED is created with a timeout of 10 minute(s)