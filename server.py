from sanic import Sanic
from api.auth import auth_bp
from api.task import task_bp

app = Sanic("multimediaSpider")

app.blueprint(auth_bp)
app.blueprint(task_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
