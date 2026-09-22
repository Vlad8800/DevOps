from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, Task, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrackHub API")


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
    return "<h1>TrackHub API running</h1>"