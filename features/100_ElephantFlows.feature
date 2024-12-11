Feature: Elephant flows
  # This feature tests various elephant flow scenarios

    Scenario: Test Elephant Flow alerts with enhanced data(7.7 device)
      Given the tenant onboard state is ONBOARDED
      And the insights are cleared
      Then push timeseries for 7 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=98, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=43000, appid=929 | 66.66       | 98             | 2                  | 4                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 120000      | 190000         | 0                  | 7                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=98, protocol=6, source_ip=10.10.0.98, source_port=43000                                                                                                                   | 227966366   | 527966366      | 2                  | 4                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 5 minute(s)
      Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 0       | 0                  | 2                  | 2                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)
    
    Scenario: Test Elephant Flow alerts with basic data(7.6 device or older)
      Given the tenant onboard state is ONBOARDED
      And the insights are cleared
      Then push timeseries for 7 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.1.98, destination_port=99, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=43000            | 66.66       | 98             | 2                  | 4                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 120000      | 190000         | 0                  | 7                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 5 minute(s)
      Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 0       | 0                  | 2                  | 2                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)
