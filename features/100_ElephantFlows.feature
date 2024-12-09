Feature: Elephant flows
  # This feature tests various elephant flow scenarios

  Scenario: Test Elephant Flow FIRING alerts
    Given the tenant onboard state is ONBOARDED
    And the insights are cleared
    When ingest the following metrics for 7 minutes
      | metric_name           | labels                                                                                                                                                                                                                | start_value | increment_type | increment_params |
      | efd_cpu_usage         | destination_ip=20.20.0.98, destination_port=98, ef_detection_time=1711367316, instance=127.0.0.3:9273, job=10.10.5.139, protocol=6, session_start_time=1711367315, source_ip=10.10.0.98, source_port=43000, appid=929 | 66.66       | linear         | slope=1          |
      | asp_drops             | asp_drops=snort-busy-not-fp, description=snort instance busy not in full proxy, instance=127.0.0.3:9273, job=10.10.5.139                                                                                              | 120000      | linear         | slope=10000      |
      | efd_total_bytes       | destination_ip=20.20.0.98, destination_port=98, protocol=6, source_ip=10.10.0.98, source_port=43000                                                                                                                   | 227966366   | linear         | slope=10000000   |
      | elephant_flow_enabled |                                                                                                                                                                                                                       | 1           | none           |                  |
    Then verify if an ELEPHANT_FLOW insight with state ACTIVE is created with a timeout of 5 minutes

  Scenario: Test Elephant Flow RESOLVED alerts
    Then verify if an ELEPHANT_FLOW insight with state RESOLVED is created with a timeout of 10 minutes
