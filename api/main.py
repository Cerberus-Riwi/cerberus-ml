import threading

from contextlib import asynccontextmanager

from fastapi import FastAPI
from api.exceptions import generic_exception_handler
from api.config import Settings
from time import perf_counter
from fastapi import Request
from api.logger import logger
from api.routers.kpis import router as kpi_router
from api.tags import tags_metadata

from consumer.rabbit_consumer import main as run_consumer


def start_consumer_thread() -> threading.Thread:
    """
    Arranca el consumer de RabbitMQ en un hilo de fondo (daemon).

    Es un hilo, no un proceso async, porque rabbit_consumer.main() usa
    pika.BlockingConnection — una librería síncrona y bloqueante que no
    puede correr dentro del event loop de FastAPI/uvicorn.

    daemon=True asegura que el hilo no impida que el proceso termine si
    uvicorn se apaga (ej. al recibir SIGTERM en Kubernetes).
    """
    thread = threading.Thread(
        target=run_consumer,
        name="rabbitmq-consumer",
        daemon=True,
    )
    thread.start()
    logger.info("Consumer de RabbitMQ arrancado en hilo de fondo (%s)", thread.name)
    return thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: arrancar el consumer junto con la API
    consumer_thread = start_consumer_thread()
    yield
    # Shutdown: no se hace join() porque el loop de pika es infinito por
    # diseño (reconexión automática); el daemon thread muere solo cuando
    # el proceso principal termina.
    logger.info(
        "API apagándose. Hilo del consumer vivo=%s",
        consumer_thread.is_alive(),
    )


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
    lifespan=lifespan,
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