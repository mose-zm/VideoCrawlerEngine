

from fastapi import FastAPI, APIRouter


task_router = APIRouter()


@task_router.get('')
async def detail_task():
    """ 详细任务。"""


@task_router.get('')
async def list_task():
    """ 任务列表。"""


def include_routers(app: FastAPI) -> None:
    app.include_router(
        task_router,
        prefix='/task'
    )
