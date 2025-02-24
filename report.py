"""
Obsidianのデイリーノートを読み込み整形されたタスクリストをターミナルに表示する
"""

import datetime
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field


class NotFoundException(Exception):
    pass


class Tag(BaseModel):
    name: str = Field(min_length=1)
    id: int


class Config(BaseModel):
    dailynote_dir: str = Field(min_length=1)
    force_tag_inheritance: bool
    parent_tag: dict[str, Tag]
    child_tag: dict[str, Tag]
    parent_default_tag: Tag
    child_default_tag: Tag


def load_config() -> Config:
    """設定を読み込む"""
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    return Config(**config)


def get_task_lines() -> list[str]:
    """今日の日付のデイリーノートを読み込み整形前のタスクリストを返す"""
    config = load_config()
    dailynote_dir = Path(config.dailynote_dir)
    filename = datetime.datetime.now().strftime("%Y-%m-%d") + ".md"
    note_path = Path(dailynote_dir) / Path(filename)

    try:
        with open(note_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        raise NotFoundException()

    return [line for line in lines if re.fullmatch(r"^\t*- \[.\] .*\n?$", line)]


def count_tabs(line: str) -> int:
    "文字列の行頭にあるタブを数える"
    n = 0
    while line.startswith("\t"):
        n += 1
        line = line.replace("\t", "", 1)
    return n


def get_tag(line: str) -> tuple[str, str]:
    """タグをサーチ・パースして親タグ、子タグのペアを返す。該当するタグがなければ空文字列を返す"""
    pattern = r"#([^\s/]*)/?(\S*)?"
    res = re.search(pattern, line)
    if res is None:
        return "", ""
    tags = res.groups()
    p_tag = tags[0] if tags[0] else ""
    c_tag = tags[1] if tags[1] else ""
    return p_tag, c_tag


class Task(BaseModel):
    content: str
    parent_tag: str
    child_tag: str


def format_line(line: str) -> str:
    """タグを除去"""
    return re.sub(r"#\S*", "", line).rstrip()


def format_tasks(task_lines: list[str]) -> list[Task]:
    """複数行にわたるタスクを整形する"""
    task_list: list[Task] = []
    while task_lines:
        parent_tag, child_tag = get_tag(task_lines[0])
        i = 0
        while (
            (len(task_lines) > 1)
            and (i < len(task_lines) - 1)
            and (count_tabs(task_lines[i + 1]) > 0)
        ):
            i += 1
        content = "\n".join([format_line(line) for line in task_lines[: i + 1]])
        task_list.append(
            Task(
                **{"content": content, "parent_tag": parent_tag, "child_tag": child_tag}
            )
        )
        task_lines = task_lines[i + 1 :]

    config = load_config()
    task_list.sort(key=lambda task: get_id(task.child_tag, config, False))
    task_list.sort(key=lambda task: get_id(task.parent_tag, config, True))

    i = 0
    while i < len(task_list) - 1:
        task, task_n = task_list[i], task_list[i + 1]
        if (task.parent_tag, task.child_tag) != (task_n.parent_tag, task_n.child_tag):
            i += 1
        else:
            task_m = Task(
                **{
                    "content": "\n".join([task.content, task_n.content]),
                    "parent_tag": task.parent_tag,
                    "child_tag": task.child_tag,
                }
            )
            del task_list[i : i + 2]
            task_list.insert(i, task_m)
    return task_list


def get_id(tag: str, config: Config, parent: bool = True) -> int:
    """タグ名からIDを取得"""
    if parent:
        tag_set = config.parent_tag
        default_tag = config.parent_default_tag
    else:
        tag_set = config.child_tag
        default_tag = config.child_default_tag
    if tag not in tag_set.keys():
        return default_tag.id
    else:
        return tag_set[tag].id


def get_name(tag: str, config: Config, parent: bool = True) -> str:
    """タグ名から分類名を取得"""
    if parent:
        tag_set = config.parent_tag
        default_tag = config.parent_default_tag
    else:
        tag_set = config.child_tag
        default_tag = config.child_default_tag
    if tag not in tag_set.keys():
        return default_tag.name
    else:
        return tag_set[tag].name


def main() -> None:
    task_lines = get_task_lines()
    tasks = format_tasks(task_lines)
    for task in tasks:
        print(task.content, end="\n\n")


if __name__ == "__main__":
    main()
