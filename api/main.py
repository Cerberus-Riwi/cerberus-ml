from fastapi import FastAPI
from api.exceptions import generic_exception_handler
from api.config import Settings
from time import perf_counter
from fastapi import Request
from api.logger import logger
from api.routers.kpis import router as kpi_router
from api.tags import tags_metadata

app = FastAPI(
    title=Settings.APP_NAME,
    version=Settings.VERSION,
    description=Settings.DESCRIPTION,
    contact={
        "name": "Cerberus Team",
        "url": "https://github.com/cerberus-riwi",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    
    openapi_tags=tags_metadata,
)

app.include_router(kpi_router)


@app.get("/")
def root():

    return {

        "service": Settings.APP_NAME,

        "version": Settings.VERSION,

        "status": "running"

    }
    
app.add_exception_handler(
    Exception,
    generic_exception_handler
)

@app.middleware("http")
async def log_requests(request: Request, call_next):

    start = perf_counter()

    response = await call_next(request)

    process_time = round((perf_counter() - start) * 1000, 2)

    response.headers["X-Process-Time"] = str(process_time)

    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )

    return response