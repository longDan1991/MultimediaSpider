from functools import wraps
from logto import LogtoClient, LogtoConfig
from sanic import json, response, redirect

client = LogtoClient(
    LogtoConfig(
        endpoint="https://1pqoyb.logto.app/",
        appId="9vho0rrkhcy5ge1a2m2l5",
        appSecret="8aQpExEYIM9IoyNCw8vQXxG5NXaJ28Nh",
    ),
)


def authenticated(shouldRedirect: bool = False, fetchUserInfo: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            print("client.isAuthenticated()", client.isAuthenticated())
            if client.isAuthenticated() is False:
                if shouldRedirect:
                    return redirect("/sign-in")
                return json({"error": "Not authenticated"}, status=401)

            request.ctx.user = (
                await client.fetchUserInfo()
                if fetchUserInfo
                else client.getIdTokenClaims()
            )
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
