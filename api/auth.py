from sanic import Blueprint, redirect, response 
from helpers.logto import get_sign_in_url, handle_sign_in, decode_id_token
import time



auth_bp = Blueprint("auth", url_prefix="/auth")


@auth_bp.route("/callback")
async def callback(request):
    try:
        if not request.ctx.session.get('signIn'):
            return response.empty();
  
        res = await handle_sign_in(
            request.ctx.session['signIn'],
            request.url
        )
        request.ctx.session['tokens'] = {
            **res.model_dump(),
            'expiresAt': res.expires_in + int(time.time() * 1000),
            'idToken': decode_id_token(res.id_token).model_dump(),
        }
        request.ctx.session['signIn'] = None
 
        return redirect('/')
    except Exception as e:
        # Change this to your error handling logic
        return response.empty();


@auth_bp.route("/sign-in")
async def sign_in(request):
    # Get the sign-in URL and redirect the user to it

    sign_in_url = await get_sign_in_url()
    request.ctx.session['signIn'] = {
        "codeVerifier": sign_in_url["codeVerifier"],
        "state": sign_in_url["state"],
        "redirectUri": sign_in_url["redirectUri"],
    }
    return redirect(sign_in_url["signInUri"])


@auth_bp.route("/sign-out")
async def sign_out(request):

    request.ctx.session['tokens'] = None
    return response.json({'message': 'Sign out successful'}) 
