import re
from functools import reduce
from pathlib import Path
from typing import List, NamedTuple, Optional, Pattern

from libcheck import LibcheckContext


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


def libcheck_has_mp3_extension(ctx: LibcheckContext) -> bool:
    return ctx.rel_path.suffix == ".mp3"


def libcheck_has_nonempty_title(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.title)


def libcheck_has_nonempty_album(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.album)


def libcheck_has_nonempty_year(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.year)


def libcheck_has_nonempty_genre(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.genre)


def libcheck_has_nonempty_albumartist(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.albumartist)


def libcheck_has_nonempty_trackno(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.track)


def libcheck_has_nonempty_discno(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.disc)


def libcheck_has_image(ctx: LibcheckContext) -> bool:
    return bool(ctx.tag.get_image())


def libcheck_path(ctx: LibcheckContext) -> bool:
    return ctx.rel_path == Path(
        sanitize1(ctx.tag.albumartist),
        f"{sanitize1(ctx.tag.year)}-{sanitize1(ctx.tag.album)}",
        f"{sanitize1(ctx.tag.disc):0>2}_{sanitize1(ctx.tag.track):0>2}"
        f"-{sanitize2(ctx.tag.title)}{ctx.rel_path.suffix}",
    )
