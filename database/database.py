"""Common functions for interacting with files and the databases.
Defines all the data types used throughout.
Common functions a large collections of items loaded into memory
being cached.
"""

import csv
import os
import string
import sys
from datetime import date, datetime
from typing import Callable, Generator, Iterable, TypeAlias, TypeVar

# Computes the exact path of the entry point file e.g. menu.py directory
PATH = (os.path.dirname(os.path.abspath(sys.argv[0]))+"/").replace("\\", "/")

DB_FILE = f"{PATH}database/database.txt"
LOG_FILE = f"{PATH}database/logfile.txt"

#Field names: keys required in a dict for it to be a part of that 'type'
FIELD_NAMES_BOOK = ("id", "title", "author", "genre", "purchase", "member")
FIELD_VISUAL_BOOK = ("id", "title", "author", "purchase", "member")
FIELD_NAMES_GROUP = ("title", "author", "genre")
FIELD_VISUAL_GROUP = ("title", "author")
FIELD_NAMES_LOG = ("id", "member", "date_out", "date_in")

DATE_FMT = "%d/%m/%Y"

# Type Aliases for type hints to make them readable
Member: TypeAlias = str # so a Member type, is just a string
Book: TypeAlias = dict[str, int | str | tuple[str, ...] | Member]
Group: TypeAlias = dict[str, str | tuple[str, ...]]
GroupHash: TypeAlias = int
Log: TypeAlias = dict[str, int | Member | date]

T = TypeVar("T", Book, Log)

def make_book(id: int, title: str, author: str, genre: tuple[str, ...], purchase: str, member: str) -> Book:
    """Creates a Book type from the fields required."""
    return dict(zip(FIELD_NAMES_BOOK, (id, title, author, genre, purchase, member)))
def _make_book_from_csv(id: str, title: str, author: str, genre: str, *args: str) -> Book:
    """Creates a Book type from the string data in a csv row."""
    return make_book(int(id), title, author, tuple(genre.split(";")), *args)
def make_log(book: int, member: str, date_out: date, date_in: date|None) -> Log:
    """Creates a Log type from the fields required."""
    return dict(zip(FIELD_NAMES_LOG, (book, member.upper(), date_out, "" if date_in is None else date_in)))
def _make_log_from_csv(book: str, member: str, do: str, di: str) -> Log:
    """Creates a Log type from the string data in a csv row."""
    return make_log(int(book), member, datetime.strptime(do, DATE_FMT).date(), datetime.strptime(di, DATE_FMT).date() if di else None)

def make_group(title: str, author: str, genre: tuple[str, ...]) -> Group:
    """Creates a Group type from the fields required."""
    return dict(zip(FIELD_NAMES_GROUP, (title, author, genre)))
def make_group_book(book: Book) -> Group:
    """Creates a Group from a Book"""
    return make_group(book["title"], book["author"], book["genre"])

def str_book(book: Book) -> Iterable[str]:
    """Maps all types in the Book back into csv row format."""
    b = book.copy()
    b["genre"] = ";".join(b["genre"])
    return map(str, (b[i] for i in FIELD_NAMES_BOOK))
def str_log(log: Log) -> Iterable[str]:
    """Maps all types in the Log back into csv row format."""
    l = log.copy()
    for k in ("date_out", "date_in"):
        l[k] = v.strftime(DATE_FMT) if (v := log[k]) else ""
    return map(str, (l[i] for i in FIELD_NAMES_LOG))

def _read(filename: str, make_func: Callable[..., T]) -> Generator[T, None, None]:
    """Wrapper around csv reader to strip first header line and make each row into type T.

    make_func: A function to convert the row into a type T
    """
    with open(filename, encoding="utf8") as file:
        it = csv.reader(file)
        next(it) # Skip the first line as it's just headers
        yield from map(lambda i: make_func(*i), it)

def _write(filename: str, str_func: Callable[[T], Iterable[str]], fieldnames: Iterable[str], it: Iterable[T]):
    """Wrapper around csv write to add the header lines and repopulate the file with rows.

    str_func: A function to convert type T into a csv row.
    fieldnames: To be inserted at the top of the file.
    it: An iterable of data of type T that will be written to the file.
    """
    with open(filename, "w", newline="", encoding="utf8") as file:
        csvw = csv.writer(file)
        csvw.writerow(map(str.title, fieldnames))
        for r in it:
            csvw.writerow(str_func(r))

__books: list[Book] | None = None
def books() -> list[Book]:
    """Return list of books

    The list is a singleton
    so that all operations on the database are atomic"""
    global __books
    # global so it conforms with singleton pattern
    if __books is None:
        __books = list(_read(DB_FILE, _make_book_from_csv))
    return __books

def save():
    """Writes the books back to the database"""
    _write(DB_FILE, str_book, FIELD_NAMES_BOOK, books())

__log: list[Log] | None = None
def logs() -> list[Log]:
    """Return list of logs

    The list is a singleton
    so that all operations on the database are atomic"""
    global __log
    # global so it conforms with singleton pattern
    if __log is None:
        __log = list(_read(LOG_FILE, _make_log_from_csv))
    return __log

def checkout():
    """Writes the logs back to the logfile"""
    _write(LOG_FILE, str_log, FIELD_NAMES_LOG, logs())

def fmt_id(id: int) -> str:
    """Format an ID with leading 0s and a hash

    Uses the size of the database to work out the required number of 0s.
    """
    return f"#{id:0{len(str(len(books())))}d}"

def from_id(id: int) -> Book:
    """Returns book object from a book ID.

    Uses the books ID to return the corresponding Book.
    Raises KeyError if the ID is not in the database.
    """
    try:
        book = books()[id]
        if book["id"] == id:
            return book
    except IndexError:    pass
    for book in books():
        if book["id"] == id:
            return book
    raise KeyError("ID does not exist")

def valid_member(member: Member) -> bool:
    """Checks if a member is a valid format.

    Must be exactly 4 characters long and only contain uppercase ascii characters.
    """
    return len(member) == 4 and all(c in string.ascii_uppercase for c in member)

__members: set[Member] | None = None
def members() -> set[Member]:
    """Return set of members

    The set is cached
    because it has to scan every log to produce it."""
    global __members
    # global so it conforms with singleton pattern
    if __members is None:
        __members = {log["member"] for log in logs()}
    return __members

def hash_group(group: Group | Book) -> GroupHash:
    """A hash function for groups.

    Can hash the books as a group is just a book with less detail.
    """
    return hash((group["title"], group["author"]))

__groups: dict[GroupHash, Group] | None = None
def group_table() -> dict[GroupHash, Group]:
    """Return a map of GroupHashes to Groups.

    The result is cached as to not need to traverse over
    the entire database every time.
    """
    global __groups
    if __groups is None:
        gs = list({hash_group(g := make_group_book(book)) : g for book in books()}.values())
        gs.sort(key=lambda g: g["title"])
        __groups = {hash_group(g): g for g in gs}
    return __groups

def groups() -> Iterable[Group]:
    """Returns an Iterable of every group."""
    return group_table().values()

if __name__ == "__main__":
    import random

    DB_FILE = f"{PATH}database.txt"
    LOG_FILE = f"{PATH}logfile.txt"

    # Loads all values from the database
    print("Books:", len(books()))
    print("Logs:", len(logs()))
    print("Groups:", len(groups()))
    print("Members:", len(members()))

    print("Hash Group & Make Group:")
    b = random.choice(books())
    assert hash_group(b) == hash_group(make_group_book(b)), "Make Group Failure"
    print("Passed")
    print("From ID:")
    try:    from_id(-1)
    except KeyError:    pass
    assert from_id(b["id"]) == b, "From ID Failure"
    print("Passed")

    # Saves Database
    save()
    checkout()

    # No runtime errors
