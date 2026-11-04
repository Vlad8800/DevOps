"""A small TrackHub event API backed by two independent PostgreSQL shards."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, create_engine, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from lab7.sharding import SHARDS, route_event


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "lab7_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str] = mapped_column(String(16), index=True)
    payload: Mapped[str] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WriteCounter(Base):
    __tablename__ = "lab7_write_counters"

    strategy: Mapped[str] = mapped_column(String(16), primary_key=True)
    counter_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


DATABASE_URLS = {
    "single": os.environ.get("LAB7_SINGLE_URL", "postgresql+psycopg2://postgres:postgres@single:5432/lab7"),
    "shard_a": os.environ.get("LAB7_SHARD_A_URL", "postgresql+psycopg2://postgres:postgres@shard_a:5432/lab7"),
    "shard_b": os.environ.get("LAB7_SHARD_B_URL", "postgresql+psycopg2://postgres:postgres@shard_b:5432/lab7"),
}
ENGINES = {name: create_engine(url, pool_pre_ping=True) for name, url in DATABASE_URLS.items()}
SESSIONS = {name: sessionmaker(bind=engine, expire_on_commit=False) for name, engine in ENGINES.items()}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for engine in ENGINES.values():
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title="TrackHub Lab 7 Sharding API", lifespan=lifespan)


class EventInput(BaseModel):
    tenant_id: int = Field(ge=0)
    event_id: UUID | None = None
    run_id: str = Field(default="manual", min_length=1, max_length=64)
    payload: str = Field(default="task event", min_length=1, max_length=200)


class EventUpdate(BaseModel):
    payload: str = Field(min_length=1, max_length=200)


def event_dict(event: Event, shard: str, bucket: int | None = None) -> dict:
    return {
        "event_id": event.event_id,
        "tenant_id": event.tenant_id,
        "run_id": event.run_id,
        "strategy": event.strategy,
        "payload": event.payload,
        "shard": shard,
        "bucket": bucket,
    }


def insert_event(node: str, body: EventInput, strategy: str, counter_key: str, bucket: int | None) -> dict:
    event_id = str(body.event_id or uuid4())
    try:
        with SESSIONS[node].begin() as session:
            event = Event(event_id=event_id, tenant_id=body.tenant_id, run_id=body.run_id,
                          strategy=strategy, payload=body.payload)
            session.add(event)
            session.execute(insert(WriteCounter).values(strategy=strategy, counter_key=counter_key, count=0)
                            .on_conflict_do_nothing(index_elements=["strategy", "counter_key"]))
            counter = session.get(WriteCounter, (strategy, counter_key))
            counter.count += 1
            work_units = int(os.environ.get("LAB7_WORK_UNITS", "0"))
            if work_units:
                session.execute(text("SELECT sum(i) FROM generate_series(1, :units) AS i"), {"units": work_units})
        return event_dict(event, node, bucket)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="event_id already exists") from exc


@app.get("/health")
def health():
    result = {}
    for name, engine in ENGINES.items():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        result[name] = "ok"
    return {"status": "ok", "nodes": result}


@app.post("/events", status_code=201)
def create_sharded_event(body: EventInput, strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    event_id = str(body.event_id or uuid4())
    body = body.model_copy(update={"event_id": UUID(event_id)})
    route = route_event(body.tenant_id, event_id, strategy)
    return insert_event(route.shard, body, strategy, route.counter_key, route.bucket)


@app.get("/events/{tenant_id}/{event_id}")
def get_sharded_event(tenant_id: int, event_id: UUID,
                      strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    route = route_event(tenant_id, str(event_id), strategy)
    with SESSIONS[route.shard]() as session:
        event = session.get(Event, str(event_id))
    if event is None or event.tenant_id != tenant_id or event.strategy != strategy:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_dict(event, route.shard, route.bucket)


@app.patch("/events/{tenant_id}/{event_id}")
def update_sharded_event(tenant_id: int, event_id: UUID, body: EventUpdate,
                         strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    route = route_event(tenant_id, str(event_id), strategy)
    with SESSIONS[route.shard].begin() as session:
        event = session.get(Event, str(event_id))
        if event is None or event.tenant_id != tenant_id or event.strategy != strategy:
            raise HTTPException(status_code=404, detail="Event not found")
        event.payload = body.payload
    return event_dict(event, route.shard, route.bucket)


@app.delete("/events/{tenant_id}/{event_id}")
def delete_sharded_event(tenant_id: int, event_id: UUID,
                         strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    route = route_event(tenant_id, str(event_id), strategy)
    with SESSIONS[route.shard].begin() as session:
        event = session.get(Event, str(event_id))
        if event is None or event.tenant_id != tenant_id or event.strategy != strategy:
            raise HTTPException(status_code=404, detail="Event not found")
        session.delete(event)
    return {"deleted": str(event_id), "shard": route.shard}


def search_node(node: str, query: str, strategy: str, run_id: str) -> dict:
    start = time.perf_counter()
    with SESSIONS[node]() as session:
        events = session.scalars(select(Event).where(Event.strategy == strategy, Event.run_id == run_id,
                                                     Event.payload == query).limit(1000)).all()
    return {"node": node, "latency_ms": round((time.perf_counter() - start) * 1000, 3),
            "events": [event_dict(event, node) for event in events]}


@app.get("/search")
def search_all(q: str = "", run_id: str = "manual",
               strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda node: search_node(node, q, strategy, run_id), SHARDS))
    return {"latency_ms": round((time.perf_counter() - start) * 1000, 3),
            "per_shard": [{"shard": r["node"], "latency_ms": r["latency_ms"]} for r in results],
            "events": [event for r in results for event in r["events"]]}


@app.get("/stats")
def stats(run_id: str, strategy: str = Query(default="bucket", pattern="^(naive|bucket)$")):
    counts = {}
    for node in SHARDS:
        with SESSIONS[node]() as session:
            counts[node] = session.scalar(select(func.count()).select_from(Event).where(
                Event.run_id == run_id, Event.strategy == strategy)) or 0
    total = sum(counts.values())
    return {"run_id": run_id, "strategy": strategy, "total": total,
            "shards": [{"name": node, "records": count,
                        "data_percent": round(count * 100 / total, 2) if total else 0,
                        "write_percent": round(count * 100 / total, 2) if total else 0}
                       for node, count in counts.items()]}


@app.post("/single/events", status_code=201)
def create_single_event(body: EventInput):
    return insert_event("single", body, "single", f"tenant:{body.tenant_id}", None)


@app.get("/single/events/{event_id}")
def get_single_event(event_id: UUID):
    with SESSIONS["single"]() as session:
        event = session.get(Event, str(event_id))
    if event is None or event.strategy != "single":
        raise HTTPException(status_code=404, detail="Event not found")
    return event_dict(event, "single")
