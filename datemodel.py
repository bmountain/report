from datetime import date
from enum import Enum, auto
from pathlib import Path

from pydantic import BaseModel


class Columns(BaseModel):
    title: str
    state: str
    start_date: str
    done_date: str


class StateStr(BaseModel):
    todo: str
    ongoing: str
    done: str
    cancelled: str


class Config(BaseModel):
    dailynote_dir: Path
    header: str
    footer: str
    state_str: StateStr
    columns: Columns


class State(Enum):
    TODO = auto()
    ONGOING = auto()
    DONE = auto()
    CANCELLED = auto()


class Task:
    def __init__(
        self,
        title: str,
        state: State,
        start_date: date | None = None,
        done_date: date | None = None,
    ) -> None:
        self.title: str = title
        self.state: State = state
        self.start_date: date | None = start_date
        self.done_date: date | None = done_date
        self.children: list[Task] = []
