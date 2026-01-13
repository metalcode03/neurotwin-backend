"""
Base API views for NeuroTwin platform.

Provides common view functionality and response formatting.
Requirements: 13.1, 13.2
"""

from typing import Any, Optional

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class BaseAPIView(APIView):
    """
    Base API view with consistent response formatting.
    
    All successful responses follow the format:
    {
        "success": true,
        "data": {...}
    }
    """
    
    def success_response(
        self, 
        data: Any = None, 
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Create a successful response with consistent format.
        
        Args:
            data: Response data
            message: Optional success message
            status_code: HTTP status code (default 200)
            
        Returns:
            Formatted Response object
        """
        response_data = {"success": True}
        
        if data is not None:
            response_data["data"] = data
        
        if message:
            response_data["message"] = message
        
        return Response(response_data, status=status_code)
    
    def created_response(
        self, 
        data: Any = None, 
        message: Optional[str] = None
    ) -> Response:
        """Create a 201 Created response."""
        return self.success_response(
            data=data, 
            message=message, 
            status_code=status.HTTP_201_CREATED
        )
    
    def no_content_response(self) -> Response:
        """Create a 204 No Content response."""
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def error_response(
        self,
        message: str,
        code: str = "ERROR",
        details: Optional[dict] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """
        Create an error response with consistent format.
        
        Args:
            message: Error message
            code: Error code
            details: Optional additional error details
            status_code: HTTP status code (default 400)
            
        Returns:
            Formatted Response object
        """
        error_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            }
        }
        
        if details:
            error_data["error"]["details"] = details
        
        return Response(error_data, status=status_code)
