@wip
Feature: Elephant flows
  Background: 
    Given the tenant onboard state is ONBOARD_SUCCESS

    Scenario: Test Elephant Flow alerts with enhanced data(7.7 device)
      Then push timeseries for 7 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                                                                        | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, client_id=929, misc_id=0, service_id=676, payload_id=-1, destination_port=98, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=43000 | 66.66       | 98             | 0                  | 3                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                                                                            | 120000      | 190000         | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=98, protocol=6, source_ip=10.10.0.98, source_port=43000                                                                                                                                                                 | 227966366   | 527966366      | 0                  | 3                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then check elephant flow insight data
      """
        {"flows" : [{
        "sourceIp": "10.10.0.98",
        "destinationIp": "20.20.0.98",
        "sourcePort": 43000,
        "destinationPort": 98,
        "protocol": 6,  
        "application": {
                        "id": 929,
                        "name": "YouTube",
                        "description": "A video-sharing website on which users can upload, share, and view videos.",
                        "riskIndex": 4
                       }
        }]}
      """
      Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 190000       | 190000        | 0                  | 1                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)
    
    Scenario: Test Elephant Flow alerts with basic data(7.6 device or older)
      Then push timeseries for 7 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.1.98, destination_port=99, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=43000            | 76.66       | 108            | 0                  | 3                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 190000      | 260000         | 0                  | 3                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then check elephant flow insight data
      """
        {"flows" : [{
        "sourceIp": "10.10.0.98",
        "destinationIp": "20.20.1.98",
        "sourcePort": 43000,
        "destinationPort": 99,
        "protocol": 6,  
        "application": {
                    "id": 0,
                    "name": null,
                    "description": null,
                    "riskIndex": 0
                }
        }]}
      """
      Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 260000      | 260000         | 0                  | 1                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)
