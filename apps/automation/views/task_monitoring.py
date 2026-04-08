"""
Celery task monitoring API endpoints.

Requirements: 27.1-27.7
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.automation.services.task_monitoring import TaskMonitoringService


class TaskStatisticsView(APIView):
    """
    Get Celery task execution statistics.
    
    Requirements: 27.1-27.7
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        summary="Get task statistics",
        description="Returns task execution statistics grouped by task name and time period",
        parameters=[
            OpenApiParameter(
                name='task_name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Optional task name to filter by',
                required=False
            ),
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Time period: hour, day, or week',
                required=False,
                enum=['hour', 'day', 'week']
            )
        ],
        responses={
            200: {
                'description': 'Task statistics',
                'content': {
                    'application/json': {
                        'example': {
                            'period': 'hour',
                            'summary': {
                                'total_tasks': 150,
                                'successful_tasks': 145,
                                'failed_tasks': 5,
                                'total_duration': 450.5,
                                'average_duration': 3.1
                            },
                            'tasks': [
                                {
                                    'task_name': 'apps.automation.tasks.process_incoming_message',
                                    'total_tasks': 100,
                                    'successful_tasks': 98,
                                    'failed_tasks': 2,
                                    'total_duration': 300.0,
                                    'average_duration': 3.06,
                                    'period': 'hour'
                                }
                            ]
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get task statistics"""
        task_name = request.query_params.get('task_name')
        period = request.query_params.get('period', 'hour')
        
        # Validate period
        if period not in ['hour', 'day', 'week']:
            return Response(
                {'error': 'Invalid period. Must be hour, day, or week.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get statistics
        monitoring_service = TaskMonitoringService()
        stats = monitoring_service.get_task_statistics(
            task_name=task_name,
            period=period
        )
        
        return Response(stats, status=status.HTTP_200_OK)


class QueueStatusView(APIView):
    """
    Get Celery queue status.
    
    Requirements: 27.1-27.7
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        summary="Get queue status",
        description="Returns current queue lengths and backlog information",
        responses={
            200: {
                'description': 'Queue status',
                'content': {
                    'application/json': {
                        'example': {
                            'queues': {
                                'high_priority': 5,
                                'incoming_messages': 120,
                                'outgoing_messages': 80,
                                'default': 10
                            },
                            'total_backlog': 215,
                            'alerts': [
                                {
                                    'queue': 'incoming_messages',
                                    'length': 120,
                                    'threshold': 100,
                                    'message': 'Queue backlog exceeds threshold'
                                }
                            ]
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get queue status"""
        monitoring_service = TaskMonitoringService()
        queue_lengths = monitoring_service.get_queue_lengths()
        
        # Calculate total backlog
        total_backlog = sum(
            length for length in queue_lengths.values() if length >= 0
        )
        
        # Check for alerts (queue backlog > 1000)
        alerts = []
        for queue_name, length in queue_lengths.items():
            if length > 1000:
                alerts.append({
                    'queue': queue_name,
                    'length': length,
                    'threshold': 1000,
                    'message': f'Queue {queue_name} backlog exceeds threshold'
                })
        
        return Response({
            'queues': queue_lengths,
            'total_backlog': total_backlog,
            'alerts': alerts
        }, status=status.HTTP_200_OK)


class WorkerStatusView(APIView):
    """
    Get Celery worker status.
    
    Requirements: 27.1-27.7
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        summary="Get worker status",
        description="Returns information about active Celery workers",
        responses={
            200: {
                'description': 'Worker status',
                'content': {
                    'application/json': {
                        'example': {
                            'active_workers': 2,
                            'workers': {
                                'celery@worker1': [
                                    {
                                        'name': 'apps.automation.tasks.process_incoming_message',
                                        'id': 'task-id-123'
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get worker status"""
        monitoring_service = TaskMonitoringService()
        worker_status = monitoring_service.get_worker_status()
        
        return Response(worker_status, status=status.HTTP_200_OK)
