from typing import Generator, Iterable
import database as db
from bookcheckout import find_log, checked_out

def is_in(book: db.Book, area: str, terms: Iterable[str]) -> Generator[bool, None, None]:
    return (term in (v if isinstance(v := book[area], str) else db.fmt_id(v)).lower() for term in terms)
def find_in(book: db.Book, terms: Iterable[str], *areas: str) -> bool:
    return all(map(any, zip(*map(lambda area: is_in(book, area, terms), areas))))

def search(title: str) -> list[db.Book]:
    """Return all books with an exactly matching title"""
    return [b for b in db.books() if title == b["title"]]

def fuzzy(term: str) -> Generator[db.Book, None, None]:
    terms = term.strip().lower().split()
    return (b for b in db.books() if find_in(b, terms, "id", "title", "author"))

def fuzzy_id(id: str) -> list[db.Book]:
    return [book for book in db.books() if id in str(book["id"])]

def old(data: list[db.Book]=None, threshold: int=60) -> list[db.Book]:
    return [b for b in (db.books() if data is None else data) if checked_out(b) and find_log(b)["date_in"]]

active_groups: list[db.Group] = []
def generate_group(term: str) -> list[db.Group]:
    global active_groups
    terms = term.strip().lower().split()
    group: set[tuple[str, str, str]] = {tuple(b[i] for i in db.FIELD_NAMES_GROUP) for b in db.books() if find_in(b, terms, "title", "author")}
    active_groups = [dict(zip(db.FIELD_NAMES_GROUP, i)) for i in sorted(group)]
    return active_groups
