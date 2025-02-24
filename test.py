import re
from typing import Any


def parse_tag(text) -> tuple[str | Any, ...] | None:
    """タグをパースして親タグ、子タグのペアを返す"""
    pattern = r"#([^\s/]*)/?(\S*)?"
    res = re.search(pattern, text)
    if res is not None:
        return res.groups()
    else:
        return None


text = "hoge #skp"
res = parse_tag(text)

print(res)
