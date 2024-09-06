from typing import Literal, Optional
import urllib.parse

from logto.OidcCore import OidcCore
from logto.models.oidc import UserInfoScope, Scope
from logto.utilities import removeFalsyKeys
from logto.LogtoClient import ReservedResource, LogtoConfig
from logto.LogtoException import LogtoException

InteractionMode = Literal["signIn", "signUp"]


config = LogtoConfig(
    endpoint="https://1pqoyb.logto.app/",
    appId="9vho0rrkhcy5ge1a2m2l5",
    appSecret="8aQpExEYIM9IoyNCw8vQXxG5NXaJ28Nh",
    scopes=[]  # "openid profile email".split(),
)

redirectUri="http://localhost:8082/api/auth/callback"

_oidcCore: Optional[OidcCore] = None


async def _getOidcCore() -> OidcCore:
    """
    Get the OIDC core object. You can use it to get the provider metadata, verify
    the ID token, fetch tokens by code or refresh token, etc.
    """
    global _oidcCore
    if _oidcCore is None:
        _oidcCore = OidcCore(
            await OidcCore.getProviderMetadata(
                f"{config.endpoint}/oidc/.well-known/openid-configuration"
            )
        )
    return _oidcCore


async def _buildSignInUrl(
    redirectUri: str,
    codeChallenge: str,
    state: str,
    interactionMode: Optional[InteractionMode] = None,
) -> str:
    appId, prompt, resources, scopes = (
        config.appId,
        config.prompt,
        config.resources,
        config.scopes,
    )
    authorizationEndpoint = (await _getOidcCore()).metadata.authorization_endpoint
    query = urllib.parse.urlencode(
        removeFalsyKeys(
            {
                "client_id": appId,
                "redirect_uri": redirectUri,
                "response_type": "code",
                "scope": " ".join(
                    (item.value if isinstance(item, Scope) else item)
                    for item in (scopes + OidcCore.defaultScopes)
                ),
                "resource": (
                    list(set(resources + [ReservedResource.organizations.value]))
                    if UserInfoScope.organizations in scopes
                    else resources
                ),
                "prompt": prompt,
                "code_challenge": codeChallenge,
                "code_challenge_method": "S256",
                "state": state,
                "interaction_mode": interactionMode,
            }
        ),
        True,
    )
    return f"{authorizationEndpoint}?{query}"


async def get_sign_in_url(interactionMode: Optional[InteractionMode] = None):
    codeVerifier = OidcCore.generateCodeVerifier()
    codeChallenge = OidcCore.generateCodeChallenge(codeVerifier)
    state = OidcCore.generateState()
    signInUrl = await _buildSignInUrl(
        redirectUri, codeChallenge, state, interactionMode
    )

    return {
        "redirectUri": redirectUri,
        "codeVerifier": codeVerifier,
        "state": state,
        "signInUri": signInUrl,
    }


async def handle_sign_in(signInSession, callbackUri):
    """
    Handle the sign-in callback from the Logto server. This method should be called
    in the callback route handler of your application.
    """
    if signInSession is None:
        raise LogtoException("Sign-in session not found")

    # Validate the callback URI without query matches the redirect URI
    parsedCallbackUri = urllib.parse.urlparse(callbackUri)

    if parsedCallbackUri.path != urllib.parse.urlparse(signInSession["redirectUri"]).path:
        raise LogtoException(
            "The URI path does not match the redirect URI in the sign-in session"
        )

    query = urllib.parse.parse_qs(parsedCallbackUri.query)

    if "error" in query:
        raise LogtoException(query["error"][0])

    if signInSession["state"] != query.get("state", [None])[0]:
        raise LogtoException("Invalid state in the callback URI")

    code = query.get("code", [None])[0]
    if code is None:
        raise LogtoException("Code not found in the callback URI")

    tokenResponse = await (await _getOidcCore()).fetchTokenByCode(
        clientId=config.appId,
        clientSecret=config.appSecret,
        redirectUri=signInSession["redirectUri"],
        code=code,
        codeVerifier=signInSession["codeVerifier"],
    )

    return tokenResponse


async def refresh_tokens(refresh_token):
    token_response = await (await _getOidcCore()).fetchTokenByRefreshToken(
        clientId=config.appId,
        clientSecret=config.appSecret,
        refreshToken=refresh_token,
    )

    return token_response

def decode_id_token(id_token):
    return OidcCore.decodeIdToken(id_token)