"""
Twin service for NeuroTwin platform.

Handles Twin creation, onboarding, and cognitive blend management.
Business logic for Twin lifecycle management.

Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
"""

from typing import Optional, Dict, Any
from django.db import transaction

from .models import Twin, OnboardingProgress
from .dataclasses import AIModel, QuestionnaireResponse, OnboardingQuestionnaire
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse as CSMQuestionnaireResponse


class TwinService:
    """
    Manages Twin lifecycle and configuration.
    
    Provides methods for onboarding, Twin creation, and cognitive blend updates.
    
    Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
    """
    
    def __init__(self):
        """Initialize TwinService with CSMService dependency."""
        self.csm_service = CSMService()
    
    def start_onboarding(self, user_id: str) -> Dict[str, Any]:
        """
        Return cognitive questionnaire for new user.
        
        Requirements: 2.1
        
        Args:
            user_id: UUID of the user starting onboarding
            
        Returns:
            Dictionary containing the questionnaire and onboarding metadata
        """
        # Check if user already has a Twin
        existing_twin = Twin.get_for_user(user_id)
        if existing_twin:
            return {
                'status': 'already_completed',
                'message': 'User already has an active Twin',
                'twin_id': str(existing_twin.id),
            }
        
        # Get or create onboarding progress
        progress, created = OnboardingProgress.objects.get_or_create(
            user_id=user_id,
            defaults={'questionnaire_responses': {}}
        )
        
        if progress.is_complete:
            return {
                'status': 'already_completed',
                'message': 'Onboarding already completed',
            }
        
        # Get the questionnaire
        questionnaire = OnboardingQuestionnaire.get_default_questionnaire()
        
        return {
            'status': 'in_progress' if not created else 'started',
            'questionnaire': questionnaire.to_dict(),
            'available_models': [
                {
                    'id': model.value,
                    'name': model.name.replace('_', ' ').title(),
                    'tier': 'free' if model in AIModel.free_tier_models() else 'paid',
                }
                for model in AIModel.all_models()
            ],
            'cognitive_blend': {
                'min': 0,
                'max': 100,
                'default': 50,
                'description': (
                    'Controls how much human personality vs AI logic your Twin uses. '
                    '0-30%: Pure AI logic with minimal personality. '
                    '31-70%: Balanced blend of personality and AI reasoning. '
                    '71-100%: Heavy personality mimicry (requires confirmation for actions).'
                ),
            },
            'saved_responses': progress.questionnaire_responses,
        }
    
    @transaction.atomic
    def complete_onboarding(
        self,
        user_id: str,
        responses: QuestionnaireResponse,
        model: AIModel,
        cognitive_blend: int
    ) -> Twin:
        """
        Create Twin with initial CSM from questionnaire responses.
        
        Requirements: 2.2, 2.4, 2.5, 2.6
        
        Args:
            user_id: UUID of the user
            responses: Completed questionnaire responses
            model: Selected AI model
            cognitive_blend: Initial cognitive blend value (0-100)
            
        Returns:
            Newly created Twin
            
        Raises:
            ValueError: If cognitive_blend is not between 0 and 100
            ValueError: If user already has an active Twin
            ValueError: If questionnaire responses are incomplete
        """
        # Validate cognitive blend
        if not 0 <= cognitive_blend <= 100:
            raise ValueError(f"Cognitive blend must be between 0 and 100, got {cognitive_blend}")
        
        # Check if user already has a Twin
        existing_twin = Twin.get_for_user(user_id)
        if existing_twin:
            raise ValueError(f"User {user_id} already has an active Twin")
        
        # Log the responses for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating twin for user {user_id}")
        logger.info(f"Responses - comm_style keys: {list(responses.communication_style.keys()) if responses.communication_style else 'None'}")
        logger.info(f"Responses - decision keys: {list(responses.decision_patterns.keys()) if responses.decision_patterns else 'None'}")
        logger.info(f"Responses - preferences keys: {list(responses.preferences.keys()) if responses.preferences else 'None'}")
        
        # Validate questionnaire responses
        if not responses.is_complete():
            # Provide detailed error message about what's missing
            missing = []
            if not responses.communication_style or len(responses.communication_style) == 0:
                missing.append("communication_style")
            if not responses.decision_patterns or len(responses.decision_patterns) == 0:
                missing.append("decision_patterns")
            if not responses.preferences or len(responses.preferences) == 0:
                missing.append("preferences")
            
            error_msg = f"Questionnaire responses are incomplete. Missing sections: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Convert to CSM questionnaire response format
        csm_responses = CSMQuestionnaireResponse(
            communication_style=responses.communication_style,
            decision_patterns=responses.decision_patterns,
            preferences=responses.preferences,
        )
        
        # Create CSM profile from questionnaire
        csm_profile = self.csm_service.create_from_questionnaire(
            user_id=user_id,
            responses=csm_responses
        )
        
        # Create the Twin
        twin = Twin.objects.create(
            user_id=user_id,
            model=model.value,
            cognitive_blend=cognitive_blend,
            csm_profile=csm_profile,
            is_active=True,
        )
        
        # Mark onboarding as complete
        OnboardingProgress.objects.filter(user_id=user_id).update(
            is_complete=True,
            questionnaire_responses=responses.to_dict(),
            selected_model=model.value,
            selected_blend=cognitive_blend,
        )
        
        return twin
    
    @transaction.atomic
    def update_cognitive_blend(self, twin_id: str, blend: int) -> Twin:
        """
        Update the cognitive blend setting (0-100).
        
        Requirements: 2.4, 2.5, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin
            blend: New cognitive blend value (0-100)
            
        Returns:
            Updated Twin
            
        Raises:
            ValueError: If blend is not between 0 and 100
            ValueError: If Twin not found
        """
        if not 0 <= blend <= 100:
            raise ValueError(f"Cognitive blend must be between 0 and 100, got {blend}")
        
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.cognitive_blend = blend
        twin.save()
        
        return twin
    
    def get_twin(self, user_id: str) -> Optional[Twin]:
        """
        Retrieve user's Twin.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Twin instance or None if not found
        """
        return Twin.get_for_user(user_id)
    
    @transaction.atomic
    def deactivate_twin(self, twin_id: str) -> bool:
        """
        Deactivate Twin (kill switch).
        
        Requirements: 2.6, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin to deactivate
            
        Returns:
            True if deactivation was successful
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.is_active = False
        twin.kill_switch_active = True
        twin.save()
        
        return True
    
    @transaction.atomic
    def reactivate_twin(self, twin_id: str) -> Twin:
        """
        Reactivate a deactivated Twin.
        
        Requirements: 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin to reactivate
            
        Returns:
            Reactivated Twin
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.is_active = True
        twin.kill_switch_active = False
        twin.save()
        
        return twin
    
    @transaction.atomic
    def update_model(self, twin_id: str, model: AIModel) -> Twin:
        """
        Update the AI model for a Twin.
        
        Requirements: 2.3, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin
            model: New AI model
            
        Returns:
            Updated Twin
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.set_ai_model(model)
        twin.save()
        
        return twin
    
    def save_onboarding_progress(
        self,
        user_id: str,
        responses: Dict[str, Any],
        model: Optional[str] = None,
        blend: Optional[int] = None
    ) -> OnboardingProgress:
        """
        Save partial onboarding progress.
        
        Args:
            user_id: UUID of the user
            responses: Partial questionnaire responses
            model: Selected AI model (optional)
            blend: Selected cognitive blend (optional)
            
        Returns:
            Updated OnboardingProgress
        """
        progress, _ = OnboardingProgress.objects.get_or_create(
            user_id=user_id,
            defaults={'questionnaire_responses': {}}
        )
        
        # Merge responses
        current_responses = progress.questionnaire_responses or {}
        current_responses.update(responses)
        progress.questionnaire_responses = current_responses
        
        if model is not None:
            progress.selected_model = model
        
        if blend is not None:
            if not 0 <= blend <= 100:
                raise ValueError(f"Cognitive blend must be between 0 and 100, got {blend}")
            progress.selected_blend = blend
        
        progress.save()
        return progress
    
    def get_twin_with_blend_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Twin with cognitive blend information.
        
        Returns detailed information about the Twin including blend mode
        and whether actions require confirmation.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dictionary with Twin info or None if not found
        """
        twin = self.get_twin(user_id)
        if not twin:
            return None
        
        # Get blended profile from CSM service
        blended_profile = None
        if twin.csm_profile:
            blended_profile = self.csm_service.apply_blend(
                twin.csm_profile,
                twin.cognitive_blend
            )
        
        return {
            'id': str(twin.id),
            'user_id': str(twin.user_id),
            'model': twin.model,
            'cognitive_blend': twin.cognitive_blend,
            'blend_mode': twin.blend_mode,
            'requires_confirmation': twin.requires_confirmation,
            'is_active': twin.is_active,
            'kill_switch_active': twin.kill_switch_active,
            'csm_profile_id': str(twin.csm_profile.id) if twin.csm_profile else None,
            'blended_profile': blended_profile,
            'created_at': twin.created_at.isoformat(),
            'updated_at': twin.updated_at.isoformat(),
        }



class AuditLogService:
    """
    Service for creating and managing audit logs.
    
    Provides structured logging for Twin actions, installations,
    uninstallations, and permission-related events.
    
    Requirements: 8.2, 18.6
    """
    
    @staticmethod
    def log_twin_action(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        cognitive_blend_value: Optional[int] = None,
        permission_flag: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log a Twin-initiated action.
        
        Requirements: 8.2, 18.6
        
        Args:
            user_id: UUID of the user
            resource_type: Type of resource (e.g., 'Workflow', 'Integration')
            resource_id: ID of the resource affected
            action: Action performed (create, update, delete, execute, etc.)
            result: Result of the action (success, failure, denied, pending)
            details: Additional context as dictionary
            cognitive_blend_value: Cognitive blend at time of action
            permission_flag: Whether permission was granted
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Create audit log entry
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='twin_action',
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
            initiated_by_twin=True,
            cognitive_blend_value=cognitive_blend_value,
            permission_flag=permission_flag,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Structured logging for monitoring
        logger.info(
            'Twin action logged',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'twin_action',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action,
                'result': result,
                'cognitive_blend': cognitive_blend_value,
                'permission_granted': permission_flag,
                'requires_attention': audit_log.requires_attention,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_installation(
        user_id: str,
        integration_type_id: str,
        integration_id: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log an integration installation event.
        
        Requirements: 18.6
        
        Args:
            user_id: UUID of the user
            integration_type_id: ID of the integration type
            integration_id: ID of the created integration
            result: Result of installation (success, failure)
            details: Additional context (OAuth scopes, errors, etc.)
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='installation',
            resource_type='Integration',
            resource_id=integration_id,
            action='create',
            result=result,
            details={
                'integration_type_id': integration_type_id,
                **(details or {})
            },
            initiated_by_twin=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            'Integration installation logged',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'installation',
                'integration_type_id': integration_type_id,
                'integration_id': integration_id,
                'result': result,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_uninstallation(
        user_id: str,
        integration_type_id: str,
        integration_id: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log an integration uninstallation event.
        
        Requirements: 18.6
        
        Args:
            user_id: UUID of the user
            integration_type_id: ID of the integration type
            integration_id: ID of the deleted integration
            result: Result of uninstallation (success, failure)
            details: Additional context (disabled workflows, errors, etc.)
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='uninstallation',
            resource_type='Integration',
            resource_id=integration_id,
            action='delete',
            result=result,
            details={
                'integration_type_id': integration_type_id,
                **(details or {})
            },
            initiated_by_twin=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            'Integration uninstallation logged',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'uninstallation',
                'integration_type_id': integration_type_id,
                'integration_id': integration_id,
                'result': result,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_permission_denied(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        initiated_by_twin: bool = False,
        cognitive_blend_value: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log a permission denied event.
        
        Requirements: 8.2, 18.6
        
        Args:
            user_id: UUID of the user
            resource_type: Type of resource access was denied for
            resource_id: ID of the resource
            action: Action that was denied
            reason: Reason for denial
            details: Additional context
            initiated_by_twin: Whether this was a Twin-initiated action
            cognitive_blend_value: Cognitive blend if Twin-initiated
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='permission_denied',
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result='denied',
            details={
                'reason': reason,
                **(details or {})
            },
            initiated_by_twin=initiated_by_twin,
            cognitive_blend_value=cognitive_blend_value,
            permission_flag=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.warning(
            'Permission denied',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'permission_denied',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action': action,
                'reason': reason,
                'initiated_by_twin': initiated_by_twin,
                'cognitive_blend': cognitive_blend_value,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_workflow_modification(
        user_id: str,
        workflow_id: str,
        action: str,
        result: str,
        changes_made: Dict[str, Any],
        reasoning: Optional[str] = None,
        initiated_by_twin: bool = False,
        cognitive_blend_value: Optional[int] = None,
        permission_flag: bool = False,
        required_confirmation: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log a workflow modification event.
        
        Requirements: 8.2, 8.6, 8.7
        
        Args:
            user_id: UUID of the user
            workflow_id: ID of the workflow
            action: Action performed (create, update, delete)
            result: Result of the action
            changes_made: Dictionary of changes (before/after values)
            reasoning: Reasoning for Twin modifications
            initiated_by_twin: Whether this was a Twin-initiated modification
            cognitive_blend_value: Cognitive blend at time of modification
            permission_flag: Whether permission was granted
            required_confirmation: Whether confirmation was required
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='workflow_modification',
            resource_type='Workflow',
            resource_id=workflow_id,
            action=action,
            result=result,
            details={
                'changes_made': changes_made,
                'reasoning': reasoning,
                'required_confirmation': required_confirmation,
            },
            initiated_by_twin=initiated_by_twin,
            cognitive_blend_value=cognitive_blend_value,
            permission_flag=permission_flag,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            'Workflow modification logged',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'workflow_modification',
                'workflow_id': workflow_id,
                'action': action,
                'result': result,
                'initiated_by_twin': initiated_by_twin,
                'cognitive_blend': cognitive_blend_value,
                'permission_granted': permission_flag,
                'required_confirmation': required_confirmation,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_kill_switch(
        user_id: str,
        twin_id: str,
        activated: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log kill switch activation or deactivation.
        
        Requirements: 8.2, 18.6
        
        Args:
            user_id: UUID of the user
            twin_id: ID of the Twin
            activated: True if activating, False if deactivating
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        event_type = 'kill_switch_activated' if activated else 'kill_switch_deactivated'
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type=event_type,
            resource_type='Twin',
            resource_id=twin_id,
            action='update',
            result='success',
            details={
                'kill_switch_active': activated,
            },
            initiated_by_twin=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.warning(
            f'Kill switch {"activated" if activated else "deactivated"}',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': event_type,
                'twin_id': twin_id,
                'activated': activated,
            }
        )
        
        return audit_log
    
    @staticmethod
    def log_cognitive_blend_change(
        user_id: str,
        twin_id: str,
        old_value: int,
        new_value: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'AuditLog':
        """
        Log cognitive blend value change.
        
        Requirements: 8.2
        
        Args:
            user_id: UUID of the user
            twin_id: ID of the Twin
            old_value: Previous cognitive blend value
            new_value: New cognitive blend value
            ip_address: IP address of the request
            user_agent: User agent string
            
        Returns:
            Created AuditLog instance
        """
        from .models import AuditLog
        import logging
        
        logger = logging.getLogger(__name__)
        
        audit_log = AuditLog.objects.create(
            user_id=user_id,
            event_type='cognitive_blend_changed',
            resource_type='Twin',
            resource_id=twin_id,
            action='update',
            result='success',
            details={
                'old_value': old_value,
                'new_value': new_value,
            },
            initiated_by_twin=False,
            cognitive_blend_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            'Cognitive blend changed',
            extra={
                'audit_log_id': str(audit_log.id),
                'user_id': user_id,
                'event_type': 'cognitive_blend_changed',
                'twin_id': twin_id,
                'old_value': old_value,
                'new_value': new_value,
            }
        )
        
        return audit_log
