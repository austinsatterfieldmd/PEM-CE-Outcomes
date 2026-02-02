"""
Okta Authentication Middleware for Vercel Serverless Functions

This module provides JWT token validation for Okta access tokens.
All API endpoints should use the @require_auth decorator to protect them.
"""

import os
import json
import functools
from urllib.request import urlopen, Request
from urllib.error import URLError
from typing import Optional, Dict, Any

# Cache for JWKS to avoid fetching on every request
_jwks_cache: Optional[Dict[str, Any]] = None

def get_okta_config() -> Dict[str, str]:
    """Get Okta configuration from environment variables."""
    issuer = os.environ.get('OKTA_ISSUER')
    audience = os.environ.get('OKTA_AUDIENCE', 'api://default')
    client_id = os.environ.get('OKTA_CLIENT_ID')

    if not issuer:
        raise ValueError('OKTA_ISSUER environment variable is required')

    return {
        'issuer': issuer,
        'audience': audience,
        'client_id': client_id,
    }

def get_jwks() -> Dict[str, Any]:
    """
    Fetch Okta's public keys for token verification.
    Keys are cached to avoid fetching on every request.
    """
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    config = get_okta_config()
    jwks_url = f"{config['issuer']}/.well-known/jwks.json"

    try:
        request = Request(jwks_url, headers={'Accept': 'application/json'})
        with urlopen(request, timeout=10) as response:
            _jwks_cache = json.loads(response.read())
            return _jwks_cache
    except URLError as e:
        raise ValueError(f'Failed to fetch JWKS from Okta: {e}')

def decode_jwt_header(token: str) -> Dict[str, Any]:
    """Decode JWT header without verification to get the key ID."""
    import base64

    try:
        header_b64 = token.split('.')[0]
        # Add padding if needed
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += '=' * padding
        header_json = base64.urlsafe_b64decode(header_b64)
        return json.loads(header_json)
    except Exception as e:
        raise ValueError(f'Invalid JWT header: {e}')

def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate Okta access token and return claims.

    Returns:
        dict with 'valid' boolean and either 'claims' or 'error'
    """
    try:
        # Import jose here to handle cases where it's not installed
        try:
            from jose import jwt, JWTError
            from jose.exceptions import JWTClaimsError, ExpiredSignatureError
        except ImportError:
            # Fallback: Accept token without validation in dev mode
            if os.environ.get('OKTA_DEV_MODE') == 'true':
                return {
                    'valid': True,
                    'claims': {'sub': 'dev-user', 'email': 'dev@example.com'},
                    'warning': 'Token not validated - dev mode'
                }
            return {
                'valid': False,
                'error': 'python-jose library not installed'
            }

        config = get_okta_config()
        jwks = get_jwks()

        # Get the key ID from the token header
        header = decode_jwt_header(token)
        kid = header.get('kid')

        if not kid:
            return {'valid': False, 'error': 'Token missing key ID'}

        # Find the matching key in JWKS
        rsa_key = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                rsa_key = key
                break

        if not rsa_key:
            return {'valid': False, 'error': 'Matching key not found in JWKS'}

        # Decode and validate the token
        claims = jwt.decode(
            token,
            rsa_key,
            algorithms=['RS256'],
            audience=config['audience'],
            issuer=config['issuer'],
            options={
                'verify_aud': True,
                'verify_iss': True,
                'verify_exp': True,
            }
        )

        return {'valid': True, 'claims': claims}

    except ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except JWTClaimsError as e:
        return {'valid': False, 'error': f'Invalid token claims: {e}'}
    except JWTError as e:
        return {'valid': False, 'error': f'Invalid token: {e}'}
    except Exception as e:
        return {'valid': False, 'error': f'Token validation failed: {e}'}

def require_auth(handler_method):
    """
    Decorator to require authentication on API endpoints.

    Usage:
        class handler(BaseHTTPRequestHandler):
            @require_auth
            def do_GET(self):
                # self.user_claims contains the validated token claims
                user_email = self.user_claims.get('email')
                ...
    """
    @functools.wraps(handler_method)
    def wrapper(self):
        # Check if auth is disabled (for local development)
        if os.environ.get('DISABLE_AUTH') == 'true':
            self.user_claims = {'sub': 'dev-user', 'email': 'dev@example.com'}
            return handler_method(self)

        # Get authorization header
        auth_header = self.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.send_header('WWW-Authenticate', 'Bearer')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Missing or invalid authorization header',
                'message': 'Please include a valid Bearer token'
            }).encode())
            return

        # Extract and validate token
        token = auth_header[7:]  # Remove 'Bearer '
        result = validate_token(token)

        if not result['valid']:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.send_header('WWW-Authenticate', 'Bearer')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Invalid token',
                'message': result.get('error', 'Token validation failed')
            }).encode())
            return

        # Token is valid, attach claims to request handler
        self.user_claims = result['claims']
        return handler_method(self)

    return wrapper

def get_user_email(claims: Dict[str, Any]) -> Optional[str]:
    """Extract user email from token claims."""
    return claims.get('email') or claims.get('sub')

def get_user_name(claims: Dict[str, Any]) -> Optional[str]:
    """Extract user name from token claims."""
    return claims.get('name') or claims.get('preferred_username')
