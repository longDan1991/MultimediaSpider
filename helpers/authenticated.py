from functools import wraps
import time 
from sanic import response, redirect

from helpers.logto import refresh_tokens, decode_id_token

def _not_auth(shouldRedirect):
    if shouldRedirect:
        return redirect("/auth/sign-in")
    return response.json({"error": "Not authenticated"}, status=401)


def authenticated(shouldRedirect: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            tokens = request.ctx.session.get("tokens")
            if not tokens:
                return _not_auth(shouldRedirect)
            
            current_time = time.time() * 1000
            
            if tokens["expiresAt"] <= current_time:
                # Access token expired, refresh for new tokens
                try:
                    res = await refresh_tokens(tokens["refresh_token"])
                    request.ctx.session["tokens"] = {
                        **res.model_dump(),
                        'expiresAt': res.expires_in + int(time.time() * 1000),
                        "idToken": decode_id_token(res.id_token).model_dump(),
                    }
                except:
                    # Exchange failed, redirect to sign in
                    return _not_auth(shouldRedirect)
            
            request.ctx.user = request.ctx.session["tokens"]["idToken"]
            
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
