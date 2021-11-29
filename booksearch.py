import database as db
from bookcheckout import find_log, checked_out

def search(title: str) -> list[db.Book]:
    """Return all books with an exactly matching title"""
    return [b for b in db.books() if title == b["title"]]

def fuzzy_id(id: str) -> list[db.Book]:
    return [book for book in db.books() if id in str(book["id"])]

def old(data: list[db.Book]=None, threshold: int=60) -> list[db.Book]:
    return [b for b in (db.books() if data is None else data) if checked_out(b) and find_log(b)["date_in"]]

active_groups: list[db.Group] = []
def generate_group(term: str) -> list[db.Group]:
    global active_groups
    term = term.lower()
    group: set[tuple[str, str, str]] = {tuple(b[i] for i in db.FIELD_NAMES_GROUP) for b in db.books() if term in b["title"].lower() or term in b["author"].lower()}
    active_groups = [dict(zip(db.FIELD_NAMES_GROUP, i)) for i in sorted(group)]
    return active_groups
