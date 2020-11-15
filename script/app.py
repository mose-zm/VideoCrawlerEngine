
from fastapi import FastAPI
from .routers import include_routers
from utils.middleware import include_exception_handler
from .version import version, title, description

app = FastAPI(
    title=title,
    version=version,
    description=description,
)

include_routers(app)
include_exception_handler(app)
