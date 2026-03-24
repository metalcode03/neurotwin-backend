"""
Automation API views.

Requirements: 7.1-7.6, 8.1-8.6, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser, HasTwin
# Temporarily commented out for Phase 1 checkpoint - Phase 2 will implement API layer
# from .services import IntegrationService, WorkflowEngine
from .services import IntegrationService, WorkflowEngine  # Legacy imports
from .dataclasses import (
    ConnectIntegrationRequest,
    UpdatePermissionsRequest,
    UpdateSteeringRulesRequest,
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
    WorkflowStepData,
)
from .serializers import (
    ConnectIntegrationSerializer,
    UpdatePermissionsSerializer,
    UpdateSteeringRulesSerializer,
    CreateWorkflowSerializer,
    ExecuteWorkflowSerializer,
)


# Integration Views

class IntegrationListView(BaseAPIView):
    """
    GET /api/v1/integrations
    
    Get all connected integrations for the user.
    Requirements: 7.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        integration_service = IntegrationService()
        integrations = integration_service.get_integrations(str(request.user.id))
        
        data = [
            {
                "id": i.id,
                "user_id": i.user_id,
                "type": i.type,
                "scopes": i.scopes,
                "steering_rules": i.steering_rules,
                "permissions": i.permissions,
                "token_expires_at": i.token_expires_at.isoformat() if i.token_expires_at else None,
                "is_active": i.is_active,
                "created_at": i.created_at.isoformat(),
            }
            for i in integrations
        ]
        
        return self.success_response(
            data={
                "integrations": data,
                "total": len(data),
            }
        )


class IntegrationConnectView(BaseAPIView):
    """
    POST /api/v1/integrations/{type}/connect
    
    Connect a new integration.
    Requirements: 7.2
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request, integration_type):
        serializer = ConnectIntegrationSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        integration_service = IntegrationService()
        
        try:
            connect_request = ConnectIntegrationRequest(
                integration_type=integration_type,
                oauth_code=serializer.validated_data['oauth_code'],
                redirect_uri=serializer.validated_data.get('redirect_uri', ''),
                requested_scopes=serializer.validated_data.get('requested_scopes'),
            )
            
            integration = integration_service.connect_integration(
                user_id=str(request.user.id),
                request=connect_request
            )
            
            return self.created_response(
                data={
                    "id": str(integration.id),
                    "type": integration.type,
                    "type_display": integration.get_type_display(),
                    "scopes": integration.scopes,
                    "permissions": integration.permissions,
                    "is_active": integration.is_active,
                },
                message=f"Connected to {integration.get_type_display()}"
            )
            
        except Exception as e:
            return self.error_response(
                message=str(e),
                code="CONNECTION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class IntegrationDetailView(BaseAPIView):
    """
    GET /api/v1/integrations/{id}
    DELETE /api/v1/integrations/{id}
    
    Get or delete a specific integration.
    Requirements: 7.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, integration_id):
        integration_service = IntegrationService()
        integration = integration_service.get_integration_by_id(integration_id)
        
        if not integration:
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if str(integration.user_id) != str(request.user.id):
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(
            data={
                "id": str(integration.id),
                "type": integration.type,
                "type_display": integration.get_type_display(),
                "scopes": integration.scopes,
                "steering_rules": integration.steering_rules,
                "permissions": integration.permissions,
                "token_expires_at": integration.token_expires_at.isoformat() if integration.token_expires_at else None,
                "is_active": integration.is_active,
                "is_token_expired": integration.is_token_expired,
                "created_at": integration.created_at.isoformat(),
            }
        )
    
    def delete(self, request, integration_id):
        integration_service = IntegrationService()
        integration = integration_service.get_integration_by_id(integration_id)
        
        if not integration:
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if str(integration.user_id) != str(request.user.id):
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        integration_service.disconnect(integration_id)
        return self.no_content_response()


class IntegrationPermissionsView(BaseAPIView):
    """
    PATCH /api/v1/integrations/{id}/permissions
    
    Update integration permissions.
    Requirements: 7.4
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def patch(self, request, integration_id):
        serializer = UpdatePermissionsSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        integration_service = IntegrationService()
        integration = integration_service.get_integration_by_id(integration_id)
        
        if not integration:
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if str(integration.user_id) != str(request.user.id):
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            update_request = UpdatePermissionsRequest(
                permissions=serializer.validated_data['permissions']
            )
            
            updated = integration_service.update_permissions(
                integration_id=integration_id,
                request=update_request
            )
            
            return self.success_response(
                data={
                    "id": str(updated.id),
                    "permissions": updated.permissions,
                },
                message="Permissions updated"
            )
            
        except Exception as e:
            return self.error_response(
                message=str(e),
                code="UPDATE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


# Workflow Views

class WorkflowListView(BaseAPIView):
    """
    GET /api/v1/workflows
    POST /api/v1/workflows
    
    List or create workflows.
    Requirements: 8.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def get(self, request):
        workflow_engine = WorkflowEngine()
        workflows = workflow_engine.get_user_workflows(str(request.user.id))
        
        data = [
            {
                "id": w.id,
                "name": w.name,
                "trigger": w.trigger,
                "steps": [
                    {
                        "integration": s.integration,
                        "action": s.action,
                        "parameters": s.parameters,
                        "requires_confirmation": s.requires_confirmation,
                        "order": s.order,
                    }
                    for s in w.steps
                ],
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat(),
            }
            for w in workflows
        ]
        
        return self.success_response(
            data={
                "workflows": data,
                "total": len(data),
            }
        )
    
    def post(self, request):
        serializer = CreateWorkflowSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        workflow_engine = WorkflowEngine()
        
        try:
            steps = [
                WorkflowStepData(
                    integration=s['integration'],
                    action=s['action'],
                    parameters=s.get('parameters', {}),
                    requires_confirmation=s.get('requires_confirmation', False),
                    order=s.get('order', idx),
                )
                for idx, s in enumerate(serializer.validated_data['steps'])
            ]
            
            create_request = CreateWorkflowRequest(
                name=serializer.validated_data['name'],
                trigger_config=serializer.validated_data['trigger_config'],
                steps=steps,
            )
            
            workflow = workflow_engine.create_workflow(
                user_id=str(request.user.id),
                request=create_request
            )
            
            return self.created_response(
                data={
                    "id": str(workflow.id),
                    "name": workflow.name,
                    "is_active": workflow.is_active,
                },
                message="Workflow created"
            )
            
        except Exception as e:
            return self.error_response(
                message=str(e),
                code="CREATE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class WorkflowDetailView(BaseAPIView):
    """
    GET /api/v1/workflows/{id}
    
    Get a specific workflow.
    Requirements: 8.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def get(self, request, workflow_id):
        workflow_engine = WorkflowEngine()
        workflow = workflow_engine.get_workflow(workflow_id)
        
        if not workflow:
            return self.error_response(
                message="Workflow not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if str(workflow.user_id) != str(request.user.id):
            return self.error_response(
                message="Workflow not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        steps = workflow.get_steps_list()
        
        return self.success_response(
            data={
                "id": str(workflow.id),
                "name": workflow.name,
                "trigger_config": workflow.trigger_config,
                "steps": steps,
                "is_active": workflow.is_active,
                "created_at": workflow.created_at.isoformat(),
            }
        )


class WorkflowExecuteView(BaseAPIView):
    """
    POST /api/v1/workflows/{id}/execute
    
    Execute a workflow.
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def post(self, request, workflow_id):
        serializer = ExecuteWorkflowSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        workflow_engine = WorkflowEngine()
        
        execute_request = ExecuteWorkflowRequest(
            workflow_id=workflow_id,
            permission_flag=serializer.validated_data['permission_flag'],
            cognitive_blend=serializer.validated_data.get('cognitive_blend', 50),
            confirmation_token=serializer.validated_data.get('confirmation_token'),
        )
        
        result = workflow_engine.execute_workflow_sync(
            user_id=str(request.user.id),
            request=execute_request
        )
        
        if result.success:
            return self.success_response(
                data={
                    "success": result.success,
                    "workflow_id": result.workflow_id,
                    "steps_completed": result.steps_completed,
                    "total_steps": result.total_steps,
                    "is_twin_generated": result.is_twin_generated,
                },
                message="Workflow executed successfully"
            )
        elif result.requires_confirmation:
            return self.error_response(
                message="User confirmation required",
                code="CONFIRMATION_REQUIRED",
                details={
                    "workflow_id": result.workflow_id,
                    "steps_completed": result.steps_completed,
                    "total_steps": result.total_steps,
                    "requires_confirmation": True,
                },
                status_code=status.HTTP_202_ACCEPTED
            )
        else:
            return self.error_response(
                message=result.error or "Workflow execution failed",
                code="EXECUTION_FAILED",
                details={
                    "workflow_id": result.workflow_id,
                    "steps_completed": result.steps_completed,
                    "total_steps": result.total_steps,
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )
