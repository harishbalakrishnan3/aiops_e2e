import os

from dotenv import load_dotenv

_endpoints = None


class Path:
    BEHAVE_FEATURES_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    )
    PROJECT_ROOT = os.path.dirname(BEHAVE_FEATURES_ROOT)
    PYTHON_UTILS_ROOT = os.path.join(PROJECT_ROOT, "utils")
    OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
    RESOURCES_DIR = os.path.join(BEHAVE_FEATURES_ROOT, "resources")


HELIOS_ASSISTANT_ID = 343

_PROD_ENV_URLS = {
    "prod": "https://www.defenseorchestrator.com",
    "prodapj": "https://www.apj.cdo.cisco.com",
    "prodeu": "https://www.defenseorchestrator.eu",
    "prodaus": "https://www.aus.cdo.cisco.com",
    "produae": "https://www.uae.cdo.cisco.com",
    "prodin": "https://www.in.cdo.cisco.com",
}


def get_base_url(env: str) -> str:
    """Return the base URL for a given environment name.

    Recognised values: prod, prodapj, prodeu, prodaus, produae, prodin,
    staging, scale, ci, or any other non-prod env slug.
    """
    env_lower = env.lower()
    if env_lower in _PROD_ENV_URLS:
        return _PROD_ENV_URLS[env_lower]
    return f"https://edge.{env_lower}.cdo.cisco.com"


class Endpoints:
    def __init__(self):
        load_dotenv()
        env = os.getenv("ENV").lower()
        self.BASE_URL = get_base_url(env)

        self.INSIGHTS_URL = self.BASE_URL + "/api/platform/ai-ops-insights/v1/insights"
        self.TENANT_ONBOARD_V2_URL = (
            self.BASE_URL + "/api/platform/ai-ops-orchestrator/v2/tenant/onboard"
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
            self.BASE_URL + "/api/platform/ai-ops-data-ingest/v2/healthmetrics"
        )
        self.PROMETHEUS_RANGE_QUERY_URL = (
            self.BASE_URL
            + "/api/platform/ai-ops-data-query/v2/healthmetrics/queryRange"
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
            self.BASE_URL + "/api/platform/ai-ops-tenant-services/v2/timeseries-stack"
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
        self.CAPACITY_ANALYTICS_DEVICE_DATA_URL = (
            self.BASE_URL + "/api/platform/ai-ops-capacity-analytics/v1/device_data"
        )


def get_endpoints():
    global _endpoints
    if _endpoints is None:
        _endpoints = Endpoints()
    return _endpoints
