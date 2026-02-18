from enum import Enum

from pydantic import BaseModel


class Device(BaseModel):
    device_name: str
    aegis_device_uid: str
    device_record_uid: str
    ra_vpn_enabled: bool = False
    container_type: str | None = None


class ScenarioEnum(str, Enum):
    ELEPHANTFLOW_LEGACY = "Test Elephant Flow alerts with multiple flows and applications for standalone device"
    ELEPHANTFLOW_ENHANCED = "Test Elephant Flow alerts with enhanced flows and applications for standalone device"
    ELEPHANTFLOW_ENHANCED_HA = (
        "Test Elephant Flow alerts with enhanced flows and applications for HA device"
    )
    ELEPHANTFLOW_ENHANCED_CLUSTER = "Test Elephant Flow alerts with enhanced flows and applications for cluster device"
    CORRELATION_CPU_LINA = (
        "Push data and test correlation alerts for CPU_LINA_THRESHOLD_BREACH"
    )
    CORRELATION_CPU_SNORT = (
        "Push data and test correlation alerts for CPU_SNORT_THRESHOLD_BREACH"
    )
    CORRELATION_HA_ACTIVE = (
        "Push data and test multi correlation alerts for HA active device"
    )
    CORRELATION_CLUSTER_CONTROL = (
        "Push data and test multi correlation alerts for CLUSTER control device"
    )
    CORRELATION_MEM_LINA = (
        "Push data and test correlation alerts for MEMORY_LINA_THRESHOLD_BREACH"
    )
    CORRELATION_MEM_SNORT = (
        "Push data and test correlation alerts for MEMORY_SNORT_THRESHOLD_BREACH"
    )
    RAVPN_FORECAST = "Testing RA-VPN forecasting"
    ANOMALY_CONNECTION = (
        "Testing Anomaly Detection for Connection Stats With Simple Linear Spike"
    )
    ANOMALY_CONNECTION_INTERMITTENT_SPIKES = (
        "Connection stats anomaly with intermittent spikes"
    )
    ANOMALY_THROUGHPUT = (
        "Testing Anomaly Detection for Throughput Stats With Simple Linear Spike"
    )
    CONNECTIONS_ANOMALY_STANDALONE = "Test CONNECTIONS_ANOMALY for standalone device"
    CONNECTIONS_ANOMALY_HA = "Test CONNECTIONS_ANOMALY for HA device"
    CAPACITY_ANALYTICS_LINA_CPU = "Test forecast insight generation for Lina CPU metric"
    CAPACITY_ANALYTICS_LINA_MEMORY = (
        "Test forecast insight generation for Lina Memory metric"
    )
    CAPACITY_ANALYTICS_SNORT_CPU = (
        "Test forecast insight generation for Snort CPU metric"
    )
    CAPACITY_ANALYTICS_SNORT_MEMORY = (
        "Test forecast insight generation for Snort Memory metric"
    )
    UNKNOWN_SCENARIO = "Unknown scenario"
