"""
Service layer for automation app.

This module contains business logic for:
- Integration type management
- App marketplace operations
- Installation workflows
- Automation template handling
- Workflow management
"""

from .integration_type import IntegrationTypeService
from .marketplace import AppMarketplaceService
from .installation import InstallationService
from .automation_template import AutomationTemplateService
from .workflow import WorkflowService

__all__ = [
    'IntegrationTypeService',
    'AppMarketplaceService',
    'InstallationService',
    'AutomationTemplateService',
    'WorkflowService',
]
