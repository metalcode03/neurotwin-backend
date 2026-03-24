"""
Structured error logging for installation and OAuth operations.

Provides consistent logging format for monitoring and debugging
installation failures, OAuth errors, and token refresh issues.

Requirements: 15.6
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from django.conf import settings


logger = logging.getLogger(__name__)


class InstallationErrorLogger:
    """
    Structured logger for installation-related errors.
    
    Provides consistent logging format with structured data for
    monitoring, alerting, and debugging.
    
    Requirements: 15.6
    """
    
    @staticmethod
    def log_oauth_error(
        user_id: str,
        integration_type_id: str,
        integration_type_name: str,
        error_type: str,
        error_details: str,
        session_id: Optional[str] = None,
        retry_count: int = 0,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log OAuth authorization or token exchange error.
        
        Args:
            user_id: User UUID
            integration_type_id: IntegrationType UUID
            integration_type_name: Human-readable integration name
            error_type: OAuth error type (e.g., 'access_denied', 'invalid_grant')
            error_details: Detailed error information
            session_id: InstallationSession UUID (optional)
            retry_count: Number of retry attempts
            additional_context: Additional context data (optional)
            
        Requirements: 15.6
        """
        log_data = {
            'event_type': 'oauth_error',
            'user_id': user_id,
            'integration_type_id': integration_type_id,
            'integration_type': integration_type_name,
            'error_type': error_type,
            'error_details': error_details,
            'retry_count': retry_count,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if session_id:
            log_data['session_id'] = session_id
        
        if additional_context:
            log_data['context'] = additional_context
        
        logger.error(
            f'OAuth error: {error_type} for {integration_type_name}',
            extra=log_data
        )
    
    @staticmethod
    def log_installation_failure(
        user_id: str,
        integration_type_id: str,
        integration_type_name: str,
        session_id: str,
        failure_phase: str,
        error_message: str,
        retry_count: int,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log installation failure.
        
        Args:
            user_id: User UUID
            integration_type_id: IntegrationType UUID
            integration_type_name: Human-readable integration name
            session_id: InstallationSession UUID
            failure_phase: Phase where failure occurred ('downloading', 'oauth_setup')
            error_message: User-friendly error message
            retry_count: Number of retry attempts
            additional_context: Additional context data (optional)
            
        Requirements: 15.6
        """
        log_data = {
            'event_type': 'installation_failure',
            'user_id': user_id,
            'integration_type_id': integration_type_id,
            'integration_type': integration_type_name,
            'session_id': session_id,
            'failure_phase': failure_phase,
            'error_message': error_message,
            'retry_count': retry_count,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if additional_context:
            log_data['context'] = additional_context
        
        logger.error(
            f'Installation failed for {integration_type_name} at phase {failure_phase}',
            extra=log_data
        )
    
    @staticmethod
    def log_token_refresh_failure(
        user_id: str,
        integration_id: str,
        integration_type_id: str,
        integration_type_name: str,
        error_type: str,
        error_details: str,
        http_status: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log OAuth token refresh failure.
        
        Args:
            user_id: User UUID
            integration_id: Integration UUID
            integration_type_id: IntegrationType UUID
            integration_type_name: Human-readable integration name
            error_type: Error type (e.g., 'invalid_grant', 'network_error')
            error_details: Detailed error information
            http_status: HTTP status code from refresh endpoint (optional)
            additional_context: Additional context data (optional)
            
        Requirements: 15.6
        """
        log_data = {
            'event_type': 'token_refresh_failure',
            'user_id': user_id,
            'integration_id': integration_id,
            'integration_type_id': integration_type_id,
            'integration_type': integration_type_name,
            'error_type': error_type,
            'error_details': error_details,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if http_status:
            log_data['http_status'] = http_status
        
        if additional_context:
            log_data['context'] = additional_context
        
        logger.error(
            f'Token refresh failed for {integration_type_name}: {error_type}',
            extra=log_data
        )
    
    @staticmethod
    def log_installation_success(
        user_id: str,
        integration_id: str,
        integration_type_id: str,
        integration_type_name: str,
        session_id: str,
        duration_seconds: float,
        retry_count: int = 0
    ) -> None:
        """
        Log successful installation completion.
        
        Args:
            user_id: User UUID
            integration_id: Created Integration UUID
            integration_type_id: IntegrationType UUID
            integration_type_name: Human-readable integration name
            session_id: InstallationSession UUID
            duration_seconds: Time taken for installation
            retry_count: Number of retry attempts before success
        """
        log_data = {
            'event_type': 'installation_success',
            'user_id': user_id,
            'integration_id': integration_id,
            'integration_type_id': integration_type_id,
            'integration_type': integration_type_name,
            'session_id': session_id,
            'duration_seconds': duration_seconds,
            'retry_count': retry_count,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.info(
            f'Installation completed for {integration_type_name}',
            extra=log_data
        )
    
    @staticmethod
    def log_uninstallation(
        user_id: str,
        integration_id: str,
        integration_type_id: str,
        integration_type_name: str,
        disabled_workflows: int,
        forced: bool = False
    ) -> None:
        """
        Log integration uninstallation.
        
        Args:
            user_id: User UUID
            integration_id: Integration UUID
            integration_type_id: IntegrationType UUID
            integration_type_name: Human-readable integration name
            disabled_workflows: Number of workflows disabled
            forced: Whether uninstallation was forced without confirmation
        """
        log_data = {
            'event_type': 'integration_uninstalled',
            'user_id': user_id,
            'integration_id': integration_id,
            'integration_type_id': integration_type_id,
            'integration_type': integration_type_name,
            'disabled_workflows': disabled_workflows,
            'forced': forced,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.info(
            f'Integration uninstalled: {integration_type_name} '
            f'({disabled_workflows} workflows disabled)',
            extra=log_data
        )
    
    @staticmethod
    def log_rate_limit_violation(
        user_id: str,
        endpoint: str,
        limit_type: str,
        current_count: int,
        max_allowed: int
    ) -> None:
        """
        Log rate limit violation.
        
        Args:
            user_id: User UUID
            endpoint: API endpoint that was rate limited
            limit_type: Type of rate limit ('installation', 'api')
            current_count: Current request count
            max_allowed: Maximum allowed requests
        """
        log_data = {
            'event_type': 'rate_limit_violation',
            'user_id': user_id,
            'endpoint': endpoint,
            'limit_type': limit_type,
            'current_count': current_count,
            'max_allowed': max_allowed,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.warning(
            f'Rate limit exceeded for user {user_id} on {endpoint}: '
            f'{current_count}/{max_allowed}',
            extra=log_data
        )
    
    @staticmethod
    def log_support_reference_generated(
        user_id: str,
        integration_type_name: str,
        session_id: str,
        support_reference: str,
        retry_count: int,
        error_summary: str
    ) -> None:
        """
        Log support reference generation after max retries.
        
        Args:
            user_id: User UUID
            integration_type_name: Human-readable integration name
            session_id: InstallationSession UUID
            support_reference: Generated support reference ID
            retry_count: Final retry count
            error_summary: Summary of the error
        """
        log_data = {
            'event_type': 'support_reference_generated',
            'user_id': user_id,
            'integration_type': integration_type_name,
            'session_id': session_id,
            'support_reference': support_reference,
            'retry_count': retry_count,
            'error_summary': error_summary,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.error(
            f'Support reference generated: {support_reference} for {integration_type_name}',
            extra=log_data
        )


class WorkflowErrorLogger:
    """
    Structured logger for workflow execution errors.
    
    Provides consistent logging for workflow failures and Twin actions.
    """
    
    @staticmethod
    def log_workflow_execution_error(
        user_id: str,
        workflow_id: str,
        workflow_name: str,
        execution_id: str,
        error_step: int,
        error_type: str,
        error_details: str,
        is_twin_generated: bool = False
    ) -> None:
        """
        Log workflow execution error.
        
        Args:
            user_id: User UUID
            workflow_id: Workflow UUID
            workflow_name: Workflow name
            execution_id: WorkflowExecution UUID
            error_step: Step index where error occurred
            error_type: Error type
            error_details: Detailed error information
            is_twin_generated: Whether workflow was Twin-generated
        """
        log_data = {
            'event_type': 'workflow_execution_error',
            'user_id': user_id,
            'workflow_id': workflow_id,
            'workflow_name': workflow_name,
            'execution_id': execution_id,
            'error_step': error_step,
            'error_type': error_type,
            'error_details': error_details,
            'is_twin_generated': is_twin_generated,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.error(
            f'Workflow execution failed: {workflow_name} at step {error_step}',
            extra=log_data
        )
    
    @staticmethod
    def log_integration_permission_denied(
        user_id: str,
        workflow_id: str,
        integration_id: str,
        integration_type_name: str,
        required_permission: str
    ) -> None:
        """
        Log integration permission denial during workflow execution.
        
        Args:
            user_id: User UUID
            workflow_id: Workflow UUID
            integration_id: Integration UUID
            integration_type_name: Integration type name
            required_permission: Permission that was denied
        """
        log_data = {
            'event_type': 'integration_permission_denied',
            'user_id': user_id,
            'workflow_id': workflow_id,
            'integration_id': integration_id,
            'integration_type': integration_type_name,
            'required_permission': required_permission,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        logger.warning(
            f'Permission denied for {integration_type_name}: {required_permission}',
            extra=log_data
        )
