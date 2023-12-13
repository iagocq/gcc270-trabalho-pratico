import datetime
import os
from contextlib import asynccontextmanager
from typing import Optional
import json

from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select, delete

class Todo(SQLModel, table=True): # type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime.date = Field(default_factory=datetime.date.today)
    content: str = Field()
    done: bool = Field(default=False)

def getenv(e: str) -> str:
    env = os.getenv(e)
    if not env:
        raise ValueError(f'Environment variable {e!r} is not set')

    return env

DB_DIALECT = getenv('DB_DIALECT')
DB_USER = getenv('DB_USER')
DB_PASSWORD = getenv('DB_PASSWORD')
DB_HOST = getenv('DB_HOST')
DB_NAME = getenv('DB_NAME')
DB_CONNECT_ARGS = json.loads(os.getenv('DB_CONNECT_ARGS', '{}'))

DB_URL = f'{DB_DIALECT}://{DB_USER}:{quote(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}'
print(DB_URL)
engine = create_engine(DB_URL, echo=True, connect_args=DB_CONNECT_ARGS)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.post('/todo')
def create_todo(todo: Todo) -> Todo:
    with Session(engine) as session:
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo

@app.get('/todo')
def read_todos() -> list[Todo]:
    with Session(engine) as session:
        todos = session.exec(select(Todo)).all()
        return list(todos)

def get_todo_by_id(session: Session, id: int) -> Optional[Todo]:
    return session.exec(
        select(Todo).where(Todo.id == id)
    ).one_or_none()

@app.put('/todo/{id}')
def update_todo(id: int, todo: Todo) -> Todo:
    with Session(engine) as session:
        db_todo = get_todo_by_id(session, id)
        if not db_todo:
            raise HTTPException(404, 'To-Do item not found')

        if todo.content is not None:
            db_todo.content = todo.content

        if todo.date is not None:
            db_todo.date = todo.date
        
        if todo.done is not None:
            db_todo.done = todo.done

        session.add(db_todo)
        session.commit()
        session.refresh(db_todo)
        return db_todo

@app.delete('/todo/{id}')
def remove_todo(id: int) -> None:
    with Session(engine) as session:
        todo = get_todo_by_id(session, id)
        if not todo:
            raise HTTPException(404, 'To-Do item not found')

        session.delete(todo)
        session.commit()
