import os

from dotenv import load_dotenv

_endpoints = None


class Path:
    BEHAVE_FEATURES_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    )
    PROJECT_ROOT = os.path.dirname(BEHAVE_FEATURES_ROOT)
    PYTHON_UTILS_ROOT = os.path.join(PROJECT_ROOT, "utils")


HELIOS_ASSISTANT_ID = 343


class Endpoints:
    def __init__(self):
        load_dotenv()
        self.BASE_URL = "https://edge.{}.cdo.cisco.com".format(os.getenv("ENV").lower())
        self.INSIGHTS_URL = self.BASE_URL + "/api/platform/ai-ops-insights/v1/insights"
        self.TENANT_ONBOARD_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v1/tenant/onboard"
        )
        self.TENANT_ONBOARD_V2_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v2/tenant/onboard"
        )
        self.TENANT_STATUS_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v1/tenant/status"
        )
        self.TENANT_STATUS_V2_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v2/tenant/status"
        )
        self.TENANT_OFFBOARD_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v1/tenant/offboard"
        )
        self.TENANT_OFFBOARD_V2_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v2/tenant/offboard"
        )
        self.DATA_INGEST_URL = (
            self.BASE_URL + "/api/platform/ai-ops-data-ingest/v1/healthmetrics"
        )
        self.PROMETHEUS_RANGE_QUERY_URL = (
            self.BASE_URL
            + "/api/platform/ai-ops-data-query/v1/healthmetrics/queryRange"
        )
        self.TRIGGER_MANAGER_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v1/trigger"
        )
        self.FMC_DETAILS_URL = (
            self.BASE_URL + "/aegis/rest/v1/services/targets/devices?q=deviceType:FMCE"
        )
        self.DEVICES_DETAILS_URL = (
            self.BASE_URL + "/aegis/rest/v1/services/targets/devices?q=deviceType:FTDC"
        )
        self.DEVICE_GATEWAY_COMMAND_URL = (
            self.BASE_URL + "/api/platform/device-gateway/command"
        )
        self.TENANT_GCM_STACK_CONFIG_URL = (
            self.BASE_URL + "/api/platform/ai-ops-tenant-services/v1/timeseries-stack"
        )
        self.AI_OPS_ANOMALY_DETECTION_FORECAST_TRIGGER_URL = (
            self.BASE_URL + "/api/platform/ai-ops-anomaly-detection/v1/trigger/forecast"
        )
        self.MODULE_SETTINGS_ENDPOINT = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v1/settings/module"
        )
        self.HELIOS_ASSISTANT = (
            "https://helios-ai-api-stage-gw.cisco.com/api/assistants"
        )
        self.HELIOS_KNOWLEDGE_BASE = (
            "https://helios-ai-api-stage-gw.cisco.com/api/knowledge_bases"
        )
        self.HELIOS_THREADS = "https://helios-ai-api-stage-gw.cisco.com/api/threads"
        self.FORECAST_DEVICE_DATA_URL = (
            self.BASE_URL + "/api/platform/ai-ops-forecast/v1/device_data"
        )


def get_endpoints():
    global _endpoints
    if _endpoints is None:
        _endpoints = Endpoints()
    return _endpoints
