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


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.1.0"}


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
def update_task_status(
    task_id: int, payload: StatusUpdate, db: Session = Depends(get_db)
):
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
  return """
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TrackHub Engine - Task Manager</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen py-10 px-4">
        <div class="max-w-4xl mx-auto space-y-6">
            <!-- Header -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl gap-4">
                <div>
                    <div class="flex items-center gap-3">
                        <span class="text-3xl">🚀</span>
                        <h1 class="text-2xl font-bold text-white tracking-tight">TrackHub Engine</h1>
                        <span id="version-badge" class="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">v1.1.0</span>
                    </div>
                    <p class="text-sm text-slate-400 mt-1">Сервіс моніторингу та керування задачами DevOps</p>
                </div>
                <div class="flex items-center gap-2 text-xs font-mono bg-slate-900/60 px-3 py-2 rounded-lg border border-slate-700">
                    <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-slate-300">Cluster Pod: Online</span>
                </div>
            </div>

            <!-- Task Form -->
            <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-lg">
                <h2 class="text-lg font-semibold text-white mb-4">Створити нову задачу</h2>
                <form id="task-form" class="grid grid-cols-1 sm:grid-cols-12 gap-3" onsubmit="handleCreateTask(event)">
                    <input type="text" id="title" placeholder="Опис задачі (наприклад, Налаштувати Ingress)..." required
                        class="sm:col-span-6 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
                    
                    <select id="service_tag" class="sm:col-span-3 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-blue-500">
                        <option value="core-api">core-api</option>
                        <option value="database">database</option>
                        <option value="k8s-cluster">k8s-cluster</option>
                        <option value="ci-pipeline">ci-pipeline</option>
                    </select>

                    <button type="submit" class="sm:col-span-3 bg-blue-600 hover:bg-blue-500 transition-colors text-white font-medium text-sm rounded-xl px-4 py-2.5 shadow-md">
                        + Додати задачу
                    </button>
                </form>
            </div>

            <!-- Task List -->
            <div class="bg-slate-800 rounded-2xl border border-slate-700 shadow-xl overflow-hidden">
                <div class="p-5 border-b border-slate-700 flex justify-between items-center">
                    <h2 class="text-lg font-semibold text-white">Список задач</h2>
                    <button onclick="loadTasks()" class="text-xs text-blue-400 hover:underline">Оновити</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-900/50 text-xs uppercase text-slate-400 border-b border-slate-700">
                            <tr>
                                <th class="px-6 py-3">ID</th>
                                <th class="px-6 py-3">Задача</th>
                                <th class="px-6 py-3">Сервіс</th>
                                <th class="px-6 py-3">Статус</th>
                                <th class="px-6 py-3 text-right">Дії</th>
                            </tr>
                        </thead>
                        <tbody id="task-tbody" class="divide-y divide-slate-700/60">
                            <!-- Tasks populated by JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            async function loadTasks() {
                const res = await fetch('/api/tasks');
                const tasks = await res.json();
                const tbody = document.getElementById('task-tbody');
                if (!tasks.length) {
                    tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-500">Задач поки немає. Створіть першу задачу вище!</td></tr>';
                    return;
                }
                tbody.innerHTML = tasks.map(t => `
                    <tr class="hover:bg-slate-700/30 transition-colors">
                        <td class="px-6 py-4 font-mono text-xs text-slate-500">#${t.id}</td>
                        <td class="px-6 py-4 font-medium text-white">${t.title}</td>
                        <td class="px-6 py-4"><span class="px-2 py-0.5 rounded text-xs bg-slate-900 border border-slate-700 text-slate-300 font-mono">${t.service_tag}</span></td>
                        <td class="px-6 py-4">
                            <span class="px-2.5 py-1 rounded-full text-xs font-medium ${t.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">
                                ${t.status}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-right space-x-2">
                            <button onclick="toggleStatus(${t.id}, '${t.status}')" class="text-xs px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200">
                                ${t.status === 'completed' ? 'Відновити' : 'Виконано'}
                            </button>
                            <button onclick="deleteTask(${t.id})" class="text-xs px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30">
                                Видалити
                            </button>
                        </td>
                    </tr>
                `).join('');
            }

            async function handleCreateTask(e) {
                e.preventDefault();
                const title = document.getElementById('title').value;
                const service_tag = document.getElementById('service_tag').value;
                await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ title, service_tag })
                });
                document.getElementById('title').value = '';
                loadTasks();
            }

            async function toggleStatus(id, currentStatus) {
                const nextStatus = currentStatus === 'completed' ? 'in_progress' : 'completed';
                await fetch(`/api/tasks/${id}`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ status: nextStatus })
                });
                loadTasks();
            }

            async function deleteTask(id) {
                await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
                loadTasks();
            }

            loadTasks();
        </script>
    </body>
    </html>
    """