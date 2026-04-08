"""
Service layer for automation app.

This module contains business logic for:
- Integration type management
- App marketplace operations
- Installation workflows
- Automation template handling
- Workflow management
- Health monitoring and observability
"""

from .integration_type import IntegrationTypeService
from .marketplace import AppMarketplaceService
from .installation import InstallationService
from .automation_template import AutomationTemplateService
from .workflow import WorkflowService
from .health_check import HealthCheckService
from .integration_health import IntegrationHealthService
from .structured_logger import StructuredLogger
from .metrics import MetricsCollector

__all__ = [
    'IntegrationTypeService',
    'AppMarketplaceService',
    'InstallationService',
    'AutomationTemplateService',
    'WorkflowService',
    'HealthCheckService',
    'IntegrationHealthService',
    'StructuredLogger',
    'MetricsCollector',
]
