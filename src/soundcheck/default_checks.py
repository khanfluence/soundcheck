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


def check_has_mp3_extension(ctx: SoundcheckContext) -> bool:
    return ctx.rel_path.suffix == ".mp3"


def check_has_nonempty_title(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.title)


def check_has_nonempty_album(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.album)


def check_has_nonempty_year(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.year)


def check_has_nonempty_genre(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.genre)


def check_has_nonempty_albumartist(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.albumartist)


def check_has_nonempty_trackno(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.track)


def check_has_nonempty_discno(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.disc)


def check_has_image(ctx: SoundcheckContext) -> bool:
    return bool(ctx.tag.get_image())


def check_path(ctx: SoundcheckContext) -> bool:
    return ctx.rel_path == Path(
        sanitize1(ctx.tag.albumartist),
        f"{sanitize1(ctx.tag.year)}-{sanitize1(ctx.tag.album)}",
        f"{sanitize1(ctx.tag.disc):0>2}_{sanitize1(ctx.tag.track):0>2}"
        f"-{sanitize2(ctx.tag.title)}{ctx.rel_path.suffix}",
    )
