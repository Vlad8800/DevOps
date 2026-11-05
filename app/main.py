import json
import os
import random
import time
from datetime import UTC, datetime
from html import escape

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.routing import Match

from app.database import Base, SessionLocal, Task, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrackHub API")

HTTP_REQUESTS = Counter(
    "trackhub_http_requests_total",
    "HTTP requests handled by TrackHub",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "trackhub_http_request_duration_seconds",
    "TrackHub HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


def route_label(request: Request) -> str:
    matched_route = request.scope.get("route")
    if matched_route is not None:
        return matched_route.path
    for candidate in app.routes:
        match, _ = candidate.matches(request.scope)
        if match == Match.FULL:
            return candidate.path
    return "unmatched"


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started = time.perf_counter()
    status = 500
    try:
        fail_rate = min(1.0, max(0.0, float(os.getenv("FAIL_RATE", "0"))))
        if request.url.path.startswith("/api/") and random.random() < fail_rate:
            response = Response(content="Simulated release failure", status_code=500)
        else:
            response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route_name = route_label(request)
        elapsed = time.perf_counter() - started
        HTTP_REQUESTS.labels(request.method, route_name, str(status)).inc()
        HTTP_DURATION.labels(request.method, route_name).observe(elapsed)
        print(
            json.dumps(
                {
                    "time": datetime.now(UTC).isoformat(),
                    "level": "error" if status >= 500 else "info",
                    "message": "http_request",
                    "method": request.method,
                    "route": route_name,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 3),
                }
            ),
            flush=True,
        )


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def app_version():
    return os.getenv("APP_VERSION", "dev")


@app.get("/health")
def health():
    return {"status": "ok", "version": app_version()}


@app.get("/version")
def version():
    return {"version": app_version()}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskCreate(BaseModel):
    title: str
    service_tag: str | None = "core-api"
    priority: str | None = "medium"


class StatusUpdate(BaseModel):
    status: str


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()


@app.post("/api/tasks")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    task = Task(
        title=payload.title.strip(),
        service_tag=payload.service_tag,
        priority=payload.priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/api/tasks/{task_id}")
def update_task_status(task_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = payload.status
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    return f"<h1>TrackHub Engine running</h1><p>Version: {escape(app_version())}</p>"
