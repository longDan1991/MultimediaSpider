from sanic import Sanic
from api import api
from tortoise.contrib.sanic import register_tortoise

app = Sanic(__name__)
app.blueprint(api)

register_tortoise(
    app,
    db_url="sqlite://data/db.sqlite3",
    modules={"models": ["models.users", "models.cookies"]},
    generate_schemas=True,
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
