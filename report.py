"""
Obsidianのデイリーノートを読み込み整形されたタスクリストをターミナルに表示する
"""

from __future__ import annotations

import datetime
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

from datemodel import Columns, Config, State, StateStr, Task


def load_config() -> tuple[
    Path,
    StateStr,
    Columns,
    str,
    str,
]:
    """設定を読み込む"""
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config = Config(**config)
    return (
        Path(config.dailynote_dir),
        config.state_str,
        config.columns,
        config.header,
        config.footer,
    )


def get_task_lines(dailynote_dir: Path) -> list[str]:
    """
    今日の日付のデイリーノートを読み込み整形前のタスクリストを返す
    タスクとして数えるのはインデントが高々1の行のみ。
    """
    filename = datetime.datetime.now().strftime("%Y-%m-%d") + ".md"
    note_path = Path(dailynote_dir) / Path(filename)

    try:
        with open(note_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        raise Exception("Task list not found")

    # チェックリスト形式の行一覧をタグを消して返す
    return [
        re.sub(r"#\S*", "", line).rstrip()
        for line in lines
        if re.fullmatch(r"^\t{,1}- \[.\] .*\n?$", line)
    ]


class StateWriter:
    def __init__(self, state_str: dict[State, str]) -> None:
        self.state_str = state_str

    def write_state(self, state: State) -> str:
        return self.state_str[state]


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
    is_parent = True if count_tabs(line) == 0 else False

    # 日付取得
    start_pattern = r"🛫\s+?((\d{4}\-)?(\d{2}\-\d{2}))"
    start_match = re.findall(start_pattern, line)
    start = start_match[0][-1] if start_match else None
    start_date = get_date(start)

    done_pattern = r"✅\s+?((\d{4}\-)?(\d{2}\-\d{2}))"
    done_match = re.findall(done_pattern, line)
    done = done_match[0][-1] if done_match else None
    done_date = get_date(done)

    #  作業状態取得
    state_pattern = r"\t{,1}\- \[(.)\] "
    if m := re.search(state_pattern, line):
        state_char = m.groups()[0]

    match state_char:
        case " ":
            state = State.TODO
        case "/":
            state = State.ONGOING
        case "x":
            state = State.DONE
        case "-":
            state = State.CANCELLED
        case _:
            raise Exception(f"Invalid state character: {state_char}")
    title = re.sub(
        "|".join([start_pattern, done_pattern, state_pattern]), "", line
    ).strip()
    return Task(title, state, start_date, done_date), is_parent


def get_date(s: str | None) -> date | None:
    """今日以前の(YYYY)-MM-DDの形式をdateにして返す"""
    if s is None:
        return None
    *_, month, day = map(int, s.split("-"))
    today = date.today()
    year = today.year
    if (d := date(year, month, day)) <= today:
        return d
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
        del task_lines[0]
    return task_list


class TableWriter:
    def __init__(self, state_str: StateStr, columns: Columns) -> None:
        self.columns = columns
        self.state_dict = {
            State.TODO: state_str.todo,
            State.ONGOING: state_str.ongoing,
            State.DONE: state_str.done,
            State.CANCELLED: state_str.cancelled,
        }

    def write_table(self, task: Task) -> str:
        rows = []
        for subtask in task.children:
            subtitle = subtask.title
            substate_str = self.state_dict[subtask.state]
            if sd := subtask.start_date:
                substart_date = sd.strftime("%m/%d")
            else:
                substart_date = ""
            if dd := subtask.done_date:
                subdone_date = dd.strftime("%m/%d")
            else:
                subdone_date = ""
            subtask_data = [subtitle, substate_str, substart_date, subdone_date]
            if subtask.state == State.CANCELLED:
                subtask_data = ["~~" + d + "~~" if d else "" for d in subtask_data]
            elif date.today() in {subtask.start_date, subtask.done_date}:
                subtask_data = ["**" + d + "**" if d else "" for d in subtask_data]
            rows.append(tuple(subtask_data))
        md_df = pd.DataFrame(
            rows,
            columns=[
                self.columns.title,
                self.columns.state,
                self.columns.start_date,
                self.columns.done_date,
            ],
        ).to_markdown(index=False)

        fmtdate = lambda d: d.strftime("%m/%d") if d else ""
        sdate_str, ddate_str = map(fmtdate, [task.start_date, task.done_date])
        table_header = "   ".join(
            [task.title, self.state_dict[task.state], sdate_str + "~" + ddate_str]
        )
        return table_header + "\n\n" + md_df


def main() -> None:
    dailynote_dir, state_str, columns, header, footer = load_config()
    task_lines = get_task_lines(dailynote_dir)
    tasks = format_tasks(task_lines)
    tw = TableWriter(state_str, columns)
    contents = "\n\n-----\n\n".join([tw.write_table(task) for task in tasks])
    print("\n\n".join([header, contents, footer]))


if __name__ == "__main__":
    main()
