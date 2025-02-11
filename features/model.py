from pydantic import BaseModel
from enum import Enum


class Device(BaseModel):
    device_name: str
    aegis_device_uid: str
    device_record_uid: str
    ra_vpn_enabled: bool


class ScenarioEnum(str, Enum):
    ELEPHANTFLOW_ENHANCED = "Test Elephant Flow alerts with enhanced data(7.7 device)"
    ELEPHANTFLOW_LEGACY = (
        "Test Elephant Flow alerts with basic data(7.6 device or older)"
    )
    CORRELATION_CPU_LINA = (
        "Push data and test correlation alerts for CPU_LINA_THRESHOLD_BREACH"
    )
    CORRELATION_CPU_SNORT = (
        "Push data and test correlation alerts for CPU_SNORT_THRESHOLD_BREACH"
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
    UNKNOWN_SCENARIO = "Unknown scenario"
