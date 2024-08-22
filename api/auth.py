from sanic import Blueprint, redirect
from helpers.authenticated import client

auth_bp = Blueprint("auth", url_prefix="/auth")


@auth_bp.route("/callback")
async def callback(request):
    try:
        await client.handleSignInCallback(request.url)  # Handle a lot of stuff
        return redirect(
            "/"
        )  # Redirect the user to the home page after a successful sign-in
    except Exception as e:
        # Change this to your error handling logic
        return "Error: " + str(e)


@auth_bp.route("/sign-in")
async def sign_in(request):
    # Get the sign-in URL and redirect the user to it
    return redirect(
        await client.signIn(
            redirectUri="http://localhost:8082/api/auth/callback",
        )
    )


@auth_bp.route("/sign-out")
async def sign_out(request):
    return redirect(
        # Redirect the user to the home page after a successful sign-out
        await client.signOut()
    )
