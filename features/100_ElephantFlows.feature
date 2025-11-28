Feature: Elephant flows
  Background: 
    Given the tenant onboard state is ONBOARD_SUCCESS


    Scenario: Test Elephant Flow alerts with multiple flows and applications for standalone device
      Then push timeseries for 4 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56324         | 20          | 26             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56324                                                                                                                 | 4000000000  | 6500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56326         | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56326                                                                                                                 | 2800000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56370          | 30          | 33             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56370                                                                                                                  | 5400000000  | 6200000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56372          | 4           | 6              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56372                                                                                                                  | 2200000000  | 2900000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56380          | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56380                                                                                                                  | 2900000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56426          | 0           | 0              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56426                                                                                                                  | 200000000   | 1200000000     | 0                  | 3                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 190000      | 260000         | 0                  | 3                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then capture the current insight timestamp
      Then check elephant flow insight data
      """
        {"flows" : [
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56324,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56326,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56370,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56372,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56380,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56426,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          }
        ]}
      """
      Then wait for 61 seconds
      Then push timeseries for 2 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56324         | 26          | 24             | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56324                                                                                                                 | 6500000000  | 6300000000     | 0                  | 2                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56326         | 13          | 12             | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56326                                                                                                                 | 3500000000  | 3300000000     | 0                  | 2                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56370          | 33          | 31             | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56370                                                                                                                  | 6200000000  | 6000000000     | 0                  | 2                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56372          | 6           | 5              | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56372                                                                                                                  | 2900000000  | 2700000000     | 0                  | 2                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56380          | 13          | 12             | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56380                                                                                                                  | 3500000000  | 3300000000     | 0                  | 2                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56426          | 0           | 0              | 0                  | 2                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56426                                                                                                                  | 1200000000  | 1100000000     | 0                  | 2                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 260000      | 270000         | 0                  | 2                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then verify the insight timestamp has been updated
      Then push timeseries for 1 minute(s) of which send last 1 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 270000      | 270000         | 0                  | 1                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)


    Scenario: Test Elephant Flow alerts with multiple flows and applications for HA device
      Then push timeseries for 4 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56324         | 20          | 26             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56324                                                                                                                 | 4000000000  | 6500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56326         | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56326                                                                                                                 | 2800000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56370          | 30          | 33             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56370                                                                                                                  | 5400000000  | 6200000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56372          | 4           | 6              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56372                                                                                                                  | 2200000000  | 2900000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56380          | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56380                                                                                                                  | 2900000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56426          | 0           | 0              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56426                                                                                                                  | 200000000   | 1200000000     | 0                  | 3                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 190000      | 260000         | 0                  | 3                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then check elephant flow insight data
      """
        {"flows" : [
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56324,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56326,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56370,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56372,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56380,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56426,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          }
        ]}
      """
      Then push timeseries for 1 minute(s) of which send last 1 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 270000      | 270000         | 0                  | 1                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)


    Scenario: Test Elephant Flow alerts with multiple flows and applications for cluster device
      Then push timeseries for 4 minute(s) of which send last 2 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56324         | 20          | 26             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56324                                                                                                                 | 4000000000  | 6500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=3306, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56326         | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=3306, protocol=6, source_ip=10.10.0.98, source_port=56326                                                                                                                 | 2800000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56370          | 30          | 33             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56370                                                                                                                  | 5400000000  | 6200000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56372          | 4           | 6              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56372                                                                                                                  | 2200000000  | 2900000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56380          | 10          | 13             | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56380                                                                                                                  | 2900000000  | 3500000000     | 0                  | 3                      |
        | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=443, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=56426          | 0           | 0              | 0                  | 3                      |
        | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=443, protocol=6, source_ip=10.10.0.98, source_port=56426                                                                                                                  | 200000000   | 1200000000     | 0                  | 3                      |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 190000      | 260000         | 0                  | 3                      |
      Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 10 minute(s)
      Then check elephant flow insight data
      """
        {"flows" : [
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56324,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56326,
            "destinationPort": 3306,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56370,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56372,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56380,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          },
          {
            "sourceIp": "10.10.0.98",
            "destinationIp": "20.20.0.98",
            "sourcePort": 56426,
            "destinationPort": 443,
            "protocol": 6,
            "application": {
              "id": 0,
              "name": null,
              "description": null,
              "riskIndex": 0
            }
          }
        ]}
      """
      Then push timeseries for 1 minute(s) of which send last 1 minute(s) of timeseries in live mode
        | metric_name           | label_values                                                                                                                                                                                                          | start_value | end_value      | start_spike_minute | spike_duration_minutes |
        | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 270000      | 270000         | 0                  | 1                      |
      Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minute(s)
