"""
Safety API views.

Requirements: 10.1-10.7, 11.1-11.5, 12.1-12.6, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser, HasTwin
from .services import PermissionService, AuditService, KillSwitchService
from .dataclasses import PermissionUpdateRequest, AuditFilterCriteria
from .serializers import (
    PermissionUpdateSerializer,
    BulkPermissionUpdateSerializer,
    AuditFilterSerializer,
    KillSwitchSerializer,
)


# Permission Views

class PermissionListView(BaseAPIView):
    """
    GET /api/v1/permissions
    PATCH /api/v1/permissions
    
    Get all permissions or update multiple permissions.
    Requirements: 10.1, 10.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        permission_service = PermissionService()
        permissions = permission_service.get_permissions(str(request.user.id))
        
        data = [
            {
                "integration": p.integration,
                "action_type": p.action_type,
                "is_granted": p.is_granted,
                "requires_approval": p.requires_approval,
                "is_high_risk": p.is_high_risk,
            }
            for p in permissions
        ]
        
        return self.success_response(
            data={
                "permissions": data,
                "total": len(data),
            }
        )
    
    def patch(self, request):
        serializer = BulkPermissionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        permission_service = PermissionService()
        updated = []
        
        for perm_data in serializer.validated_data['permissions']:
            update_request = PermissionUpdateRequest(
                integration=perm_data['integration'],
                action_type=perm_data['action_type'],
                is_granted=perm_data.get('is_granted'),
                requires_approval=perm_data.get('requires_approval'),
                reason=perm_data.get('reason', '')
            )
            
            permission = permission_service.update_permission(
                user_id=str(request.user.id),
                request=update_request
            )
            
            updated.append({
                "integration": permission.integration,
                "action_type": permission.action_type,
                "is_granted": permission.is_granted,
                "requires_approval": permission.requires_approval,
            })
        
        return self.success_response(
            data={"updated": updated},
            message=f"Updated {len(updated)} permission(s)"
        )



class PermissionDetailView(BaseAPIView):
    """
    GET /api/v1/permissions/{integration}/{action_type}
    PATCH /api/v1/permissions/{integration}/{action_type}
    
    Get or update a specific permission.
    Requirements: 10.1, 10.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, integration, action_type):
        permission_service = PermissionService()
        permission = permission_service.get_permission(
            user_id=str(request.user.id),
            integration=integration,
            action_type=action_type
        )
        
        if not permission:
            return self.error_response(
                message="Permission not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(
            data={
                "integration": permission.integration,
                "action_type": permission.action_type,
                "is_granted": permission.is_granted,
                "requires_approval": permission.requires_approval,
                "is_high_risk": permission.is_high_risk,
            }
        )
    
    def patch(self, request, integration, action_type):
        serializer = PermissionUpdateSerializer(data={
            **request.data,
            'integration': integration,
            'action_type': action_type,
        })
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        permission_service = PermissionService()
        
        update_request = PermissionUpdateRequest(
            integration=integration,
            action_type=action_type,
            is_granted=serializer.validated_data.get('is_granted'),
            requires_approval=serializer.validated_data.get('requires_approval'),
            reason=serializer.validated_data.get('reason', '')
        )
        
        permission = permission_service.update_permission(
            user_id=str(request.user.id),
            request=update_request
        )
        
        return self.success_response(
            data={
                "integration": permission.integration,
                "action_type": permission.action_type,
                "is_granted": permission.is_granted,
                "requires_approval": permission.requires_approval,
            },
            message="Permission updated"
        )


# Audit Views

class AuditListView(BaseAPIView):
    """
    GET /api/v1/audit
    
    Get audit history with filtering.
    Requirements: 11.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        serializer = AuditFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        audit_service = AuditService()
        
        filters = AuditFilterCriteria(
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
            action_type=serializer.validated_data.get('action_type'),
            target_integration=serializer.validated_data.get('target_integration'),
            outcome=serializer.validated_data.get('outcome'),
        )
        
        entries = audit_service.get_audit_history(
            user_id=str(request.user.id),
            filters=filters,
            limit=serializer.validated_data.get('limit', 100),
            offset=serializer.validated_data.get('offset', 0)
        )
        
        total = audit_service.count_audit_entries(
            user_id=str(request.user.id),
            filters=filters
        )
        
        data = [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action_type": e.action_type,
                "target_integration": e.target_integration,
                "outcome": e.outcome,
                "cognitive_blend": e.cognitive_blend,
                "is_twin_generated": e.is_twin_generated,
            }
            for e in entries
        ]
        
        return self.success_response(
            data={
                "entries": data,
                "total": total,
            }
        )


class AuditDetailView(BaseAPIView):
    """
    GET /api/v1/audit/{id}
    
    Get a specific audit entry with full details.
    Requirements: 11.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, entry_id):
        audit_service = AuditService()
        entry = audit_service.get_audit_entry(entry_id)
        
        if not entry:
            return self.error_response(
                message="Audit entry not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if entry.user_id != str(request.user.id):
            return self.error_response(
                message="Audit entry not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(
            data={
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "action_type": entry.action_type,
                "target_integration": entry.target_integration,
                "input_data": entry.input_data,
                "outcome": entry.outcome,
                "cognitive_blend": entry.cognitive_blend,
                "reasoning_chain": entry.reasoning_chain,
                "is_twin_generated": entry.is_twin_generated,
                "checksum": entry.checksum,
            }
        )


class AuditVerifyView(BaseAPIView):
    """
    GET /api/v1/audit/{id}/verify
    
    Verify integrity of an audit entry.
    Requirements: 11.2
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, entry_id):
        audit_service = AuditService()
        entry = audit_service.get_audit_entry(entry_id)
        
        if not entry:
            return self.error_response(
                message="Audit entry not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if entry.user_id != str(request.user.id):
            return self.error_response(
                message="Audit entry not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        is_valid = audit_service.verify_log_integrity(entry_id)
        
        return self.success_response(
            data={
                "entry_id": entry_id,
                "is_valid": is_valid,
                "checksum": entry.checksum,
            }
        )


# Kill Switch Views

class KillSwitchStatusView(BaseAPIView):
    """
    GET /api/v1/kill-switch
    
    Get kill switch status.
    Requirements: 12.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        kill_switch_service = KillSwitchService()
        status_data = kill_switch_service.get_kill_switch_status(str(request.user.id))
        
        return self.success_response(
            data={
                "is_active": status_data.is_active,
                "activated_at": status_data.activated_at.isoformat() if status_data.activated_at else None,
                "activated_by": status_data.activated_by,
                "reason": status_data.reason,
            }
        )


class KillSwitchActivateView(BaseAPIView):
    """
    POST /api/v1/kill-switch/activate
    
    Activate the kill switch.
    Requirements: 12.1, 12.2
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        serializer = KillSwitchSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        kill_switch_service = KillSwitchService()
        
        status_data = kill_switch_service.activate_kill_switch(
            user_id=str(request.user.id),
            reason=serializer.validated_data.get('reason', ''),
            triggered_by="user"
        )
        
        return self.success_response(
            data={
                "is_active": status_data.is_active,
                "activated_at": status_data.activated_at.isoformat() if status_data.activated_at else None,
            },
            message="Kill switch activated. All automations halted."
        )


class KillSwitchDeactivateView(BaseAPIView):
    """
    POST /api/v1/kill-switch/deactivate
    
    Deactivate the kill switch.
    Requirements: 12.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def post(self, request):
        serializer = KillSwitchSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        kill_switch_service = KillSwitchService()
        
        status_data = kill_switch_service.deactivate_kill_switch(
            user_id=str(request.user.id),
            reason=serializer.validated_data.get('reason', ''),
            triggered_by="user"
        )
        
        return self.success_response(
            data={"is_active": status_data.is_active},
            message="Kill switch deactivated. Automations re-enabled."
        )


# Actions Views (Undo functionality)

class ReversibleActionsView(BaseAPIView):
    """
    GET /api/v1/actions
    
    Get reversible actions that can be undone.
    Requirements: 12.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        kill_switch_service = KillSwitchService()
        
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
        include_undone = request.query_params.get('include_undone', 'false').lower() == 'true'
        
        actions = kill_switch_service.get_reversible_actions(
            user_id=str(request.user.id),
            include_expired=include_expired,
            include_undone=include_undone,
        )
        
        data = [
            {
                "id": a.action_id,
                "action_type": a.action_type,
                "target_integration": a.target_integration,
                "undo_deadline": a.undo_deadline.isoformat(),
                "is_undone": a.is_undone,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ]
        
        return self.success_response(
            data={
                "actions": data,
                "total": len(data),
            }
        )


class ActionUndoView(BaseAPIView):
    """
    POST /api/v1/actions/{id}/undo
    
    Undo a reversible action.
    Requirements: 12.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request, action_id):
        kill_switch_service = KillSwitchService()
        
        # Check undo window first
        undo_deadline = kill_switch_service.get_undo_window(action_id)
        
        if undo_deadline is None:
            return self.error_response(
                message="Action cannot be undone (not found, expired, or already undone)",
                code="UNDO_NOT_AVAILABLE",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        success = kill_switch_service.undo_action(action_id)
        
        if not success:
            return self.error_response(
                message="Failed to undo action",
                code="UNDO_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            data={"action_id": action_id, "undone": True},
            message="Action undone successfully"
        )


class ActionApproveView(BaseAPIView):
    """
    POST /api/v1/actions/{id}/approve
    
    Approve a pending action.
    Requirements: 10.7, 12.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request, action_id):
        # TODO: Implement action approval logic
        # This should:
        # 1. Verify the action exists and is pending
        # 2. Check user has permission to approve
        # 3. Execute the approved action
        # 4. Log the approval in audit trail
        
        return self.success_response(
            data={"action_id": action_id, "approved": True},
            message="Action approved successfully"
        )


class ActionRejectView(BaseAPIView):
    """
    POST /api/v1/actions/{id}/reject
    
    Reject a pending action.
    Requirements: 10.7, 12.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request, action_id):
        # TODO: Implement action rejection logic
        # This should:
        # 1. Verify the action exists and is pending
        # 2. Check user has permission to reject
        # 3. Mark the action as rejected
        # 4. Log the rejection in audit trail
        
        return self.success_response(
            data={"action_id": action_id, "rejected": True},
            message="Action rejected successfully"
        )
