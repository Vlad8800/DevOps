
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, Task, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevOps TrackHub")

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
        service_tag=payload.service_tag or "core-api",
        priority=payload.priority or "medium",
        status="pending"
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
def serve_ui():
    return """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrackHub // DevOps Lab 1</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #090d16;
            --bg-card: rgba(17, 24, 39, 0.7);
            --border-card: rgba(255, 255, 255, 0.08);
            --accent-glow: rgba(56, 189, 248, 0.15);
            --primary: #38bdf8;
            --primary-hover: #0ea5e9;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --tag-bg: #1e293b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
            background-image: 
                radial-gradient(at 10% 20%, rgba(56, 189, 248, 0.07) 0px, transparent 50%),
                radial-gradient(at 90% 80%, rgba(99, 102, 241, 0.07) 0px, transparent 50%);
        }

        .container { max-width: 900px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-card);
        }

        .brand { display: flex; align-items: center; gap: 12px; }
        .logo-box {
            background: linear-gradient(135deg, #0284c7, #6366f1);
            width: 38px; height: 38px; border-radius: 8px;
            display: grid; place-items: center; font-weight: 700; color: #fff;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
        }
        h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
        .subtitle { font-size: 13px; color: var(--text-muted); }

        .system-pill {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            background: #10b98118;
            color: #34d399;
            border: 1px solid #10b98130;
            padding: 6px 12px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .system-pill::before {
            content: ""; display: inline-block; width: 6px; height: 6px;
            border-radius: 50%; background: #34d399; box-shadow: 0 0 8px #34d399;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 16px 20px;
        }
        .stat-title { font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
        .stat-num { font-size: 24px; font-weight: 700; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }

        .action-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(8px);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 24px;
        }

        .form-row { display: grid; grid-template-columns: 2fr 1fr 1fr auto; gap: 10px; }
        input, select {
            background: #0f172a;
            border: 1px solid #334155;
            color: var(--text-main);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus, select:focus { border-color: var(--primary); }

        .btn-primary {
            background: var(--primary);
            color: #04101e;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }

        .task-list { display: flex; flex-direction: column; gap: 10px; }
        .task-item {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(8px);
            border-radius: 10px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: border-color 0.2s, transform 0.2s;
        }
        .task-item:hover { border-color: rgba(56, 189, 248, 0.3); }

        .task-left { display: flex; align-items: center; gap: 12px; }
        .task-title { font-size: 14px; font-weight: 600; }
        .task-title.completed { text-decoration: line-through; color: var(--text-muted); }

        .badge {
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .badge-tag { background: #1e293b; color: #93c5fd; }
        .badge-high { background: #7f1d1d40; color: #f87171; border: 1px solid #dc262630; }
        .badge-medium { background: #78350f40; color: #fbbf24; border: 1px solid #d9770630; }
        .badge-low { background: #14532d40; color: #4ade80; border: 1px solid #16a34a30; }

        .task-right { display: flex; align-items: center; gap: 8px; }
        .btn-status {
            background: transparent;
            border: 1px solid #334155;
            color: var(--text-muted);
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
            cursor: pointer;
        }
        .btn-status:hover { border-color: var(--text-main); color: var(--text-main); }
        .btn-del {
            background: transparent;
            border: none;
            color: #ef4444;
            padding: 6px 10px;
            font-size: 16px;
            cursor: pointer;
            opacity: 0.7;
        }
        .btn-del:hover { opacity: 1; }
        .empty-state { text-align: center; color: var(--text-muted); padding: 40px 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="logo-box">TH</div>
                <div>
                    <h1>TrackHub Engine</h1>
                    <div class="subtitle">Distributed Tasks & Services Control Plane</div>
                </div>
            </div>
            <div class="system-pill">PostgreSQL 15 Connected</div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">Всього задач</div>
                <div class="stat-num" id="count-total">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">В процесі</div>
                <div class="stat-num" id="count-progress" style="color: #fbbf24;">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Виконано</div>
                <div class="stat-num" id="count-done" style="color: #34d399;">0</div>
            </div>
        </div>

        <div class="action-card">
            <form id="task-form" class="form-row" onsubmit="handleCreate(event)">
                <input id="in-title" type="text" placeholder="Опис завдання або процесу..." required autocomplete="off" />
                <input id="in-tag" type="text" placeholder="Сервіс (напр. auth, core)" />
                <select id="in-priority">
                    <option value="low">Low Priority</option>
                    <option value="medium" selected>Medium Priority</option>
                    <option value="high">High Priority</option>
                </select>
                <button type="submit" class="btn-primary">+ Створити</button>
            </form>
        </div>

        <div class="task-list" id="task-container">
            <div class="empty-state">Завантаження даних із PostgreSQL...</div>
        </div>
    </div>

    <script>
        async function fetchTasks() {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            render(data);
        }

        function render(tasks) {
            const container = document.getElementById('task-container');
            document.getElementById('count-total').innerText = tasks.length;
            document.getElementById('count-progress').innerText = tasks.filter(t => t.status === 'in_progress').length;
            document.getElementById('count-done').innerText = tasks.filter(t => t.status === 'completed').length;

            if (tasks.length === 0) {
                container.innerHTML = '<div class="empty-state">Завдань ще немає. Додайте перший сервісний таск вище.</div>';
                return;
            }

            container.innerHTML = tasks.map(t => `
                <div class="task-item">
                    <div class="task-left">
                        <span class="badge badge-${t.priority}">${t.priority}</span>
                        <span class="badge badge-tag">${t.service_tag}</span>
                        <span class="task-title ${t.status === 'completed' ? 'completed' : ''}">${escapeHtml(t.title)}</span>
                    </div>
                    <div class="task-right">
                        <select class="btn-status" onchange="changeStatus(${t.id}, this.value)">
                            <option value="pending" ${t.status === 'pending' ? 'selected' : ''}>Очікує</option>
                            <option value="in_progress" ${t.status === 'in_progress' ? 'selected' : ''}>В роботі</option>
                            <option value="completed" ${t.status === 'completed' ? 'selected' : ''}>Готово</option>
                        </select>
                        <button class="btn-del" onclick="deleteTask(${t.id})" title="Видалити">&times;</button>
                    </div>
                </div>
            `).join('');
        }

        async function handleCreate(e) {
            e.preventDefault();
            const title = document.getElementById('in-title').value;
            const service_tag = document.getElementById('in-tag').value || 'core-api';
            const priority = document.getElementById('in-priority').value;

            await fetch('/api/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title, service_tag, priority })
            });

            document.getElementById('in-title').value = '';
            document.getElementById('in-tag').value = '';
            fetchTasks();
        }

        async function changeStatus(id, status) {
            await fetch(`/api/tasks/${id}`, {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ status })
            });
            fetchTasks();
        }

        async function deleteTask(id) {
            await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            fetchTasks();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        fetchTasks();
    </script>
</body>
</html>
    """