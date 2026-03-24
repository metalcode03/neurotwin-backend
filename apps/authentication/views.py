"""
Authentication API views.

Requirements: 1.1-1.7, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.api.views import BaseAPIView
from core.api.throttling import AuthRateThrottle
from .services import AuthService
from .serializers import (
    RegisterSerializer,
    VerifyEmailSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    OAuthCallbackSerializer,
    LogoutSerializer,
)


class RegisterView(BaseAPIView):
    """
    POST /api/v1/auth/register
    
    Create a new user account and send verification email.
    Requirements: 1.1
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=RegisterSerializer,
        responses={201: OpenApiResponse(description="Account created successfully")},
        auth=[],  # No auth required
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.register(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="REGISTRATION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.created_response(
            data={"user_id": result.user_id},
            message="Account created. Please check your email for verification link."
        )


class VerifyEmailView(BaseAPIView):
    """
    POST /api/v1/auth/verify
    
    Verify email address using token from verification email.
    Requirements: 1.2
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: OpenApiResponse(description="Email verified successfully")},
        auth=[],
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.verify_email(
            token=serializer.validated_data['token']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="VERIFICATION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            data={"user_id": result.user_id},
            message="Email verified successfully. You can now log in."
        )


class LoginView(BaseAPIView):
    """
    POST /api/v1/auth/login
    
    Authenticate user and return JWT tokens.
    Requirements: 1.3, 1.4
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="Login successful, returns JWT tokens")},
        auth=[],  # No auth required
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.login(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="AUTHENTICATION_FAILED",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        return self.success_response(
            data={
                "user_id": result.user_id,
                "access_token": result.token,
                "refresh_token": result.refresh_token,
            }
        )


class RefreshTokenView(BaseAPIView):
    """
    POST /api/v1/auth/refresh
    
    Refresh access token using refresh token.
    Requirements: 1.6
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: OpenApiResponse(description="Token refreshed successfully")},
        auth=[],
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.refresh_access_token(
            refresh_token=serializer.validated_data['refresh_token']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="TOKEN_REFRESH_FAILED",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        return self.success_response(
            data={
                "user_id": result.user_id,
                "access_token": result.token,
                "refresh_token": result.refresh_token,
            }
        )


class PasswordResetRequestView(BaseAPIView):
    """
    POST /api/v1/auth/password-reset
    
    Request password reset email.
    Requirements: 1.7
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Password reset email sent if account exists")},
        auth=[],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        # Always returns True to prevent email enumeration
        auth_service.request_password_reset(
            email=serializer.validated_data['email']
        )
        
        return self.success_response(
            message="If an account exists with this email, a password reset link has been sent."
        )


class PasswordResetView(BaseAPIView):
    """
    POST /api/v1/auth/password-reset/confirm
    
    Reset password using token from reset email.
    Requirements: 1.7
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=PasswordResetSerializer,
        responses={200: OpenApiResponse(description="Password reset successfully")},
        auth=[],
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.reset_password(
            token=serializer.validated_data['token'],
            new_password=serializer.validated_data['new_password']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="PASSWORD_RESET_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            message="Password reset successfully. You can now log in with your new password."
        )


class OAuthView(BaseAPIView):
    """
    GET /api/v1/auth/oauth/{provider}
    
    Initiate OAuth flow for the specified provider.
    Requirements: 1.5
    """
    permission_classes = [AllowAny]
    
    @extend_schema(auth=[])
    def get(self, request, provider):
        # TODO: Implement OAuth redirect to provider
        return self.error_response(
            message=f"OAuth with {provider} is not yet implemented",
            code="NOT_IMPLEMENTED",
            status_code=status.HTTP_501_NOT_IMPLEMENTED
        )


class OAuthCallbackView(BaseAPIView):
    """
    POST /api/v1/auth/oauth/{provider}/callback
    
    Handle OAuth callback from provider.
    Requirements: 1.5
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    
    @extend_schema(
        request=OAuthCallbackSerializer,
        responses={200: OpenApiResponse(description="OAuth login successful")},
        auth=[],
    )
    def post(self, request, provider):
        serializer = OAuthCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        result = auth_service.oauth_callback(
            provider=provider,
            code=serializer.validated_data['code']
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="OAUTH_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            data={
                "user_id": result.user_id,
                "access_token": result.token,
                "refresh_token": result.refresh_token,
            }
        )


class LogoutView(BaseAPIView):
    """
    POST /api/v1/auth/logout
    
    Logout by invalidating refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service = AuthService()
        success = auth_service.logout(
            refresh_token=serializer.validated_data['refresh_token']
        )
        
        if not success:
            return self.error_response(
                message="Failed to logout",
                code="LOGOUT_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(message="Logged out successfully")


class LogoutAllView(BaseAPIView):
    """
    POST /api/v1/auth/logout-all
    
    Logout from all devices by invalidating all tokens.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        auth_service = AuthService()
        count = auth_service.logout_all_devices(str(request.user.id))
        
        return self.success_response(
            data={"tokens_invalidated": count},
            message="Logged out from all devices"
        )


class CurrentUserView(BaseAPIView):
    """
    GET /api/v1/auth/me
    
    Get current authenticated user profile.
    Requirements: 4.4
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: OpenApiResponse(description="Current user profile")},
    )
    def get(self, request):
        user = request.user
        
        return self.success_response(
            data={
                "id": str(user.id),
                "email": user.email,
                "username": "",  # Not yet implemented in User model
                "display_name": "",  # Not yet implemented in User model
                "profile_image": None,  # Not yet implemented in User model
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "oauth_provider": user.oauth_provider,
            }
        )
