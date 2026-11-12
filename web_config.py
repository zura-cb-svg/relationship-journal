import os
from dotenv import load_dotenv
from fastapi import HTTPException, Request, Response

load_dotenv()
ALLOWED_ORIGINS = [item.strip() for item in os.getenv(
    'CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173'
).split(',') if item.strip()]
if '*' in ALLOWED_ORIGINS:
    raise RuntimeError('Wildcard CORS is not allowed')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() in ('true', '1')
REFRESH_COOKIE = 'rj_refresh'

def check_auth_origin(request: Request):
    origin = request.headers.get('origin')
    own_origin = str(request.base_url).rstrip('/')
    if origin is not None and origin not in [own_origin, *ALLOWED_ORIGINS]:
        raise HTTPException(status_code=403, detail='Origin not allowed')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(status_code=403, detail='Cross-site authentication is not allowed')

def set_refresh_cookie(response: Response, token: str, seconds: int):
    response.set_cookie(REFRESH_COOKIE, token, max_age=seconds, path='/',
                        httponly=True, secure=COOKIE_SECURE, samesite='strict')

def clear_refresh_cookie(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path='/', httponly=True,
                           secure=COOKIE_SECURE, samesite='strict')
