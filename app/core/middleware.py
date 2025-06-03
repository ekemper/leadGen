from typing import List
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

from app.services.auth_service import AuthService
from app.core.database import SessionLocal, get_db
from app.core.logger import get_logger

logger = get_logger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle authentication for protected endpoints.
    Only signup and signin endpoints are unprotected.
    """
    
    # Define unprotected endpoints (public routes)
    UNPROTECTED_PATHS = {
        "/api/v1/auth/signup",
        "/api/v1/auth/login", 
        "/api/v1/health",
        "/api/v1/health/",
        "/api/v1/health/ready",
        "/api/v1/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
    }
    
    # Paths that start with these prefixes are also unprotected
    UNPROTECTED_PREFIXES = {
        "/docs",
        "/redoc",
        "/static",
    }

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and check authentication for protected endpoints.
        """
        path = request.url.path
        method = request.method
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)
        
        # Check if path is unprotected
        if self._is_unprotected_path(path):
            return await call_next(request)
        
        # Extract and validate token for protected endpoints
        try:
            token = self._extract_token(request)
            if not token:
                return self._unauthorized_response("Token is missing")
            
            # Validate token and get user
            user = await self._validate_token(token)
            if not user:
                return self._unauthorized_response("Invalid token")
            
            # Add user to request state for use in endpoints
            request.state.current_user = user
            
        except HTTPException as e:
            return self._unauthorized_response(e.detail)
        except Exception as e:
            logger.error(f"Authentication error for {path}: {str(e)}")
            return self._unauthorized_response("Authentication failed")
        
        return await call_next(request)
    
    def _is_unprotected_path(self, path: str) -> bool:
        """Check if the path is unprotected."""
        # Exact match
        if path in self.UNPROTECTED_PATHS:
            return True
        
        # Prefix match
        for prefix in self.UNPROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header.split(" ")[1]
    
    async def _validate_token(self, token: str):
        """Validate JWT token and return user."""
        auth_service = AuthService()
        
        # Check if we're in a test environment
        # In tests, we need to use the test database configuration
        if os.getenv('PYTEST_CURRENT_TEST') or 'pytest' in os.getenv('_', ''):
            # Use the dependency injection system for database session
            # This ensures we use the test database in tests
            from app.main import app
            if get_db in app.dependency_overrides:
                db_generator = app.dependency_overrides[get_db]()
                db = next(db_generator)
                try:
                    user = auth_service.get_current_user(token, db)
                    return user
                finally:
                    try:
                        next(db_generator)
                    except StopIteration:
                        pass
            else:
                # Fallback to regular session
                db = SessionLocal()
                try:
                    user = auth_service.get_current_user(token, db)
                    return user
                finally:
                    db.close()
        else:
            # Production/development - use regular session
            db = SessionLocal()
            try:
                user = auth_service.get_current_user(token, db)
                return user
            finally:
                db.close()
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return standardized unauthorized response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "error": {
                    "code": 401,
                    "name": "Unauthorized",
                    "message": message
                }
            },
            headers={
                "WWW-Authenticate": "Bearer",
                "Access-Control-Allow-Origin": "http://localhost:5173",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        ) 