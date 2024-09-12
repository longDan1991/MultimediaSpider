from sanic import Sanic
from api import api
from tortoise.contrib.sanic import register_tortoise 
from packages.sanic_session.db_session import TortoiseSessionInterface
from packages.sanic_session import Session

app = Sanic(__name__)
app.blueprint(api)
Session(app, interface=TortoiseSessionInterface())

register_tortoise(
    app,
    db_url="sqlite://data/db.sqlite3",
    modules={"models": ["models.users", "models.cookies", "models.sessions", "models.tasks"]},
    generate_schemas=True,
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
