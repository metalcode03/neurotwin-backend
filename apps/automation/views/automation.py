"""
WorkflowViewSet for automation management.

Handles workflow CRUD operations with grouping by integration type.
Requirements: 10.7-10.9
"""

import logging
from collections import defaultdict

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from apps.automation.models import Workflow, IntegrationTypeModel
from apps.automation.serializers import (
    WorkflowSerializer,
    WorkflowListSerializer,
    WorkflowCreateSerializer,
)
from apps.automation.services import WorkflowService

logger = logging.getLogger(__name__)


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workflow management.
    
    Provides:
    - list: GET /api/v1/automations/ - List workflows grouped by integration type
    - retrieve: GET /api/v1/automations/{id}/ - Get workflow details
    - create: POST /api/v1/automations/ - Create new workflow
    - update: PUT/PATCH /api/v1/automations/{id}/ - Update workflow
    - destroy: DELETE /api/v1/automations/{id}/ - Delete workflow
    
    Requirements: 10.7-10.9
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - list: WorkflowListSerializer (lightweight)
        - create: WorkflowCreateSerializer (simplified)
        - retrieve, update, partial_update: WorkflowSerializer (full)
        """
        if self.action == 'list':
            return WorkflowListSerializer
        elif self.action == 'create':
            return WorkflowCreateSerializer
        return WorkflowSerializer
    
    def get_queryset(self):
        """
        Get queryset with filtering.
        
        Supports query parameters:
        - integration_type_id: Filter by integration type
        - is_enabled: Filter by enabled status
        - is_custom: Filter by custom vs template workflows
        
        Requirements: 10.7
        """
        queryset = Workflow.objects.filter(
            user=self.request.user
        ).select_related(
            'automation_template',
            'automation_template__integration_type'
        ).order_by('-created_at')
        
        # Apply filters from query parameters
        integration_type_id = self.request.query_params.get('integration_type_id')
        if integration_type_id:
            # Filter workflows that use this integration type in their steps
            # Note: This requires checking JSON field, so we filter in Python
            # For better performance, consider adding a many-to-many relationship
            pass  # Will be filtered in list() method
        
        is_enabled = self.request.query_params.get('is_enabled')
        if is_enabled is not None:
            queryset = queryset.filter(is_active=is_enabled.lower() == 'true')
        
        is_custom = self.request.query_params.get('is_custom')
        if is_custom is not None:
            queryset = queryset.filter(is_custom=is_custom.lower() == 'true')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        List workflows grouped by integration type.
        
        Query parameters:
        - integration_type_id: Filter by integration type
        - is_enabled: Filter by enabled status (true/false)
        - is_custom: Filter by custom workflows (true/false)
        - grouped: Return grouped by integration type (default: true)
        
        Response format (grouped=true):
            {
                "workflows_by_integration": {
                    "integration_type_id": {
                        "integration_type": {...},
                        "workflows": [...]
                    }
                },
                "total": 10
            }
        
        Response format (grouped=false):
            {
                "workflows": [...],
                "total": 10
            }
        
        Requirements: 10.7
        """
        queryset = self.get_queryset()
        
        # Check if grouping is requested
        grouped = request.query_params.get('grouped', 'true').lower() == 'true'
        
        # Apply integration_type_id filter if provided
        integration_type_id = request.query_params.get('integration_type_id')
        if integration_type_id:
            # Filter workflows that use this integration type
            filtered_workflows = []
            for workflow in queryset:
                integration_types_used = workflow.get_integration_types_used()
                if integration_type_id in integration_types_used:
                    filtered_workflows.append(workflow)
            queryset = filtered_workflows
        
        serializer = self.get_serializer(queryset, many=True)
        
        if not grouped:
            # Return flat list
            return Response({
                'workflows': serializer.data,
                'total': len(serializer.data)
            })
        
        # Group workflows by integration type
        workflows_by_integration = defaultdict(lambda: {
            'integration_type': None,
            'workflows': []
        })
        
        for workflow_data in serializer.data:
            # Get integration types used in this workflow
            integration_types_used = workflow_data.get('integration_types_used', [])
            
            if not integration_types_used:
                # Workflow has no integration types (shouldn't happen, but handle gracefully)
                continue
            
            # Add workflow to each integration type it uses
            for integration_type_id in integration_types_used:
                workflows_by_integration[integration_type_id]['workflows'].append(workflow_data)
        
        # Fetch integration type details for each group
        integration_type_ids = list(workflows_by_integration.keys())
        integration_types = IntegrationTypeModel.objects.filter(
            id__in=integration_type_ids
        ).values('id', 'type', 'name', 'icon', 'category')
        
        # Map integration type details to groups
        for integration_type in integration_types:
            integration_type_id = str(integration_type['id'])
            if integration_type_id in workflows_by_integration:
                workflows_by_integration[integration_type_id]['integration_type'] = integration_type
        
        return Response({
            'groups': [
                {
                    'integration_type': group_data['integration_type'],
                    'workflows': group_data['workflows']
                }
                for group_data in workflows_by_integration.values()
                if group_data['integration_type']  # Only include groups with valid integration type
            ],
            'total': len(serializer.data)
        })
    
    def create(self, request, *args, **kwargs):
        """
        Create a new workflow with validation.
        
        Request body:
            {
                "name": "My Workflow",
                "trigger_config": {...},
                "steps": [
                    {
                        "action_type": "send_message",
                        "integration_type_id": "uuid",
                        "parameters": {...}
                    }
                ],
                "is_active": true
            }
        
        Requirements: 10.8
        """
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create workflow using service layer
            workflow = WorkflowService.create_workflow(
                user=request.user,
                name=serializer.validated_data['name'],
                trigger_config=serializer.validated_data['trigger_config'],
                steps=serializer.validated_data['steps'],
                is_twin_generated=False
            )
            
            # Serialize response
            response_serializer = WorkflowSerializer(workflow)
            
            logger.info(
                f'Workflow created: id={workflow.id}, user={request.user.id}, '
                f'name={workflow.name}'
            )
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(
                f'Workflow creation failed: user={request.user.id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Workflow creation failed',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update a workflow (PUT).
        
        Requirements: 10.8
        """
        return self._update_workflow(request, partial=False)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a workflow (PATCH).
        
        Supports Twin modifications with safety checks:
        - permission_flag: Required for Twin modifications
        - cognitive_blend: Cognitive blend value (0-100)
        - requires_confirmation: Whether confirmation was obtained for high blend
        
        Requirements: 10.8, 8.1-8.7
        """
        return self._update_workflow(request, partial=True)
    
    def _update_workflow(self, request, partial=False):
        """
        Internal method to handle workflow updates.
        
        Supports Twin modification tracking and safety checks.
        """
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Extract Twin modification parameters
            modified_by_twin = request.data.get('modified_by_twin', False)
            cognitive_blend = request.data.get('cognitive_blend', 50)
            permission_flag = request.data.get('permission_flag', False)
            
            # Update workflow using service layer (with Twin safety checks)
            workflow = WorkflowService.update_workflow(
                workflow_id=instance.id,
                user=request.user,
                updates=serializer.validated_data,
                modified_by_twin=modified_by_twin,
                cognitive_blend=cognitive_blend,
                permission_flag=permission_flag
            )
            
            # Serialize response
            response_serializer = WorkflowSerializer(workflow)
            
            logger.info(
                f'Workflow updated: id={workflow.id}, user={request.user.id}, '
                f'by_twin={modified_by_twin}, blend={cognitive_blend}'
            )
            
            return Response(response_serializer.data)
            
        except PermissionError as e:
            logger.warning(
                f'Workflow update permission denied: id={instance.id}, '
                f'user={request.user.id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Permission denied',
                    'detail': str(e)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(
                f'Workflow update failed: id={instance.id}, '
                f'user={request.user.id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Workflow update failed',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a workflow.
        
        For template-based workflows, requires confirmation via query parameter.
        
        Query parameters:
            - force: Set to 'true' to skip confirmation for template workflows
        
        Requirements: 10.9
        """
        instance = self.get_object()
        force = request.query_params.get('force', 'false').lower() == 'true'
        
        # Check if confirmation is required for template workflows
        if not instance.is_custom and not force:
            return Response(
                {
                    'error': 'Confirmation required',
                    'detail': 'This workflow was created from a template. '
                             'Set force=true to confirm deletion.',
                    'requires_confirmation': True,
                    'workflow_name': instance.name,
                    'template_name': instance.automation_template.name if instance.automation_template else None
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Delete workflow
        workflow_id = instance.id
        workflow_name = instance.name
        instance.delete()
        
        logger.info(
            f'Workflow deleted: id={workflow_id}, user={request.user.id}, '
            f'name={workflow_name}'
        )
        
        return Response(
            {
                'success': True,
                'message': f'Workflow "{workflow_name}" deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def change_history(self, request, pk=None):
        """
        Get change history for a workflow.
        
        GET /api/v1/automations/{id}/change_history/
        
        Returns all modifications to the workflow with:
        - Author (User or Twin)
        - Timestamp
        - Changes made (before/after values)
        - Reasoning (for Twin modifications)
        - Cognitive blend value (for Twin modifications)
        - Permission and confirmation flags
        
        Requirements: 8.7
        """
        from apps.automation.models import WorkflowChangeHistory
        from apps.automation.serializers import WorkflowChangeHistorySerializer
        
        workflow = self.get_object()
        
        # Get change history ordered by most recent first
        history = WorkflowChangeHistory.objects.filter(
            workflow=workflow
        ).select_related('user').order_by('-created_at')
        
        serializer = WorkflowChangeHistorySerializer(history, many=True)
        
        return Response({
            'workflow_id': str(workflow.id),
            'workflow_name': workflow.name,
            'change_history': serializer.data,
            'total_changes': history.count()
        })
