"""
Obsidianのデイリーノートを読み込み整形されたタスクリストをターミナルに表示する
"""

from __future__ import annotations

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import datetime
import json
import re
import sys
from datetime import date
from enum import Enum, auto
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field


class NotFoundException(Exception):
    pass


class Tag(BaseModel):
    name: str = Field(min_length=1)
    id: int


class Config(BaseModel):
    dailynote_dir: str = Field(min_length=1)


def load_config() -> Config:
    """設定を読み込む"""
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    return Config(**config)


def get_task_lines() -> list[str]:
    """
    今日の日付のデイリーノートを読み込み整形前のタスクリストを返す
    タスクとして数えるのはインデントが高々1の行のみ。
    """
    config = load_config()
    dailynote_dir = Path(config.dailynote_dir)
    filename = datetime.datetime.now().strftime("%Y-%m-%d") + ".md"
    note_path = Path(dailynote_dir) / Path(filename)

    try:
        with open(note_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        raise NotFoundException()

    return [line for line in lines if re.fullmatch(r"^\t{,1}- \[.\] .*\n?$", line)]


class State(Enum):
    TODO = auto()
    ONGOING = auto()
    DONE = auto()


def get_state_str(state: State) -> str:
    if state == State.TODO:
        return "未着手"
    elif state == State.ONGOING:
        return "作業中"
    elif state == State.DONE:
        return "完了"
    else:
        raise Exception()


class Task:
    def __init__(
        self,
        title: str,
        state: State,
        start: date | None = None,
        done: date | None = None,
    ) -> None:
        self.title: str = title
        self.state: State = state
        self.start: date | None = start
        self.done: date | None = done
        self.children: list[Task] = []


def count_tabs(line: str) -> int:
    "文字列の行頭にあるタブを数える"
    n = 0
    while line.startswith("\t"):
        n += 1
        line = line.replace("\t", "", 1)
    return n


def parse_line(line: str) -> tuple[Task, bool]:
    """
    タスク一行を読み取りそのtitle, start, doneを返す。
    さらにそれが親タスクか返す
    title: タスク内容
    start: 開始日
    done: 終了日
    """
    line = re.sub(r"#\S*", "", line).rstrip()
    is_parent = True if count_tabs(line) == 0 else False

    # 日付取得
    start_pattern = r"🛫\s+?((\d{4}\-)?(\d{2}\-\d{2}))"
    done_pattern = r"✅\s+?((\d{4}\-)?(\d{2}\-\d{2}))"
    start_match = re.findall(start_pattern, line)
    start = start_match[0][-1] if start_match else None
    done_match = re.findall(done_pattern, line)
    done = done_match[0][-1] if done_match else None
    start = get_date(start)
    done = get_date(done)

    state_pattern = r"\t{,1}\- \[(.)\] "
    state_char = re.search(state_pattern, line).groups()[0]
    state: State
    if state_char == " ":
        state = State.TODO
    elif state_char == "/":
        state = State.ONGOING
    elif state_char == "x":
        state = State.DONE
    else:
        print("state_char:", state_char)
        raise Exception()
    title = re.sub(
        "|".join([start_pattern, done_pattern, state_pattern]), "", line
    ).strip()
    return Task(title, state, start, done), is_parent


def get_date(s: str | None) -> date | None:
    """今日以前のMM-DDの形式をdateにして返す"""
    if s is None:
        return None
    month, day = map(int, s.split("-"))
    today = date.today()
    year = today.year
    if date(year, month, day) <= today:
        return date(year, month, day)
    else:
        return date(year - 1, month, day)


def format_tasks(task_lines: list[str]) -> list[Task]:
    """複数行にわたるタスクを整形する"""
    task_list: list[Task] = []
    while task_lines:
        task, is_parent = parse_line(task_lines[0])
        if is_parent:
            task_list.append(task)
        else:
            task_list[-1].children.append(task)
        task_lines = task_lines[1:]
    return task_list


def get_table(task: Task) -> tuple[str, date | None, date | None, str]:
    """タスクを読み込んでその情報とサブタスクの表（md形式）を返す。"""
    title, start, done = task.title, task.start, task.done
    df = pd.DataFrame(
        [
            (subtask.title, get_state_str(subtask.state), subtask.start, subtask.done)
            for subtask in task.children
        ],
        columns=["作業", "状態", "開始", "終了"],
    )
    df_md = df.to_markdown(index=False)
    return title, start, done, df_md


def main() -> None:
    task_lines = get_task_lines()
    tasks = format_tasks(task_lines)
    res = ""
    for i, task in enumerate(tasks):
        title, start, done, md = get_table(task)
        header = title + f" {get_state_str(task.state)} 開始：{start} 終了：{done}"
        res += "\n".join([header, md])
        if i < len(tasks) - 1:
            res += "\n-----\n"

    print(res)


if __name__ == "__main__":
    main()
