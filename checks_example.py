import re
from functools import reduce
from pathlib import Path
from typing import List, NamedTuple, Optional, Pattern

from soundcheck import SoundcheckContext


class Sub(NamedTuple):
    pattern: Pattern
    repl: str


SUBS: List[Sub] = [
    Sub(re.compile(r"[*]"), "."),
    Sub(re.compile(r"[?]"), ""),
    Sub(re.compile(r"[:/\\]"), "-"),
    Sub(re.compile(r"[<>|]"), "_"),
]


def sanitize1(string: Optional[str]) -> str:
    return (
        reduce(lambda s, sub: re.sub(sub.pattern, sub.repl, s), SUBS, string)
        if string
        else ""
    )


def sanitize2(string: Optional[str]) -> str:
    return sanitize1(string).strip(".").rstrip()


def check_has_mp3_extension(context: SoundcheckContext) -> bool:
    return context.file_path.relative_to(context.lib_root).suffix == ".mp3"


def check_has_nonempty_title(context: SoundcheckContext) -> bool:
    return bool(context.tag.title)


def check_has_nonempty_album(context: SoundcheckContext) -> bool:
    return bool(context.tag.album)


def check_has_nonempty_year(context: SoundcheckContext) -> bool:
    return bool(context.tag.year)


def check_has_nonempty_genre(context: SoundcheckContext) -> bool:
    return bool(context.tag.genre)


def check_has_nonempty_albumartist(context: SoundcheckContext) -> bool:
    return bool(context.tag.albumartist)


def check_has_nonempty_trackno(context: SoundcheckContext) -> bool:
    return bool(context.tag.track)


def check_has_nonempty_discno(context: SoundcheckContext) -> bool:
    return bool(context.tag.disc)


def check_has_image(context: SoundcheckContext) -> bool:
    return bool(context.tag.get_image())


def check_path(context: SoundcheckContext) -> bool:
    rel_path: Path = context.file_path.relative_to(context.lib_root)
    return rel_path == Path(
        sanitize1(context.tag.albumartist),
        f"{sanitize1(context.tag.year)}-{sanitize1(context.tag.album)}",
        f"{sanitize1(context.tag.disc):0>2}_{sanitize1(context.tag.track):0>2}"
        f"-{sanitize2(context.tag.title)}{rel_path.suffix}",
    )
