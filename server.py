from api import api
from tortoise.contrib.sanic import register_tortoise
from models import sanic_models
from packages.sanic_session.db_session import TortoiseSessionInterface
from packages.sanic_session import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from helpers.sanic import app

app.blueprint(api)
Session(app, interface=TortoiseSessionInterface())

register_tortoise(
    app,
    db_url="sqlite://data/db.sqlite3",
    modules={"models": sanic_models},
    generate_schemas=True,
)


# 定义定时任务
async def scheduled_task():
    print(f"定时任务执行于: {datetime.now()}")


# 创建调度器
scheduler = AsyncIOScheduler()
scheduler.add_job(scheduled_task, "interval", minutes=30)


@app.listener("before_server_start")
async def start_scheduler(app, loop):
    scheduler.start()


@app.listener("after_server_stop")
async def stop_scheduler(app, loop):
    scheduler.shutdown()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
