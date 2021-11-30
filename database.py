import csv
from datetime import date, datetime
from typing import Callable, Generator, Iterable, TypeAlias, TypeVar

DB_FILE = "database.1.txt"
LOG_FILE = "logfile.txt"
FIELD_NAMES_BOOK = ("id", "title", "author", "genre", "purchase", "member")
FIELD_VISUAL_BOOK = ("id", "title", "author", "purchase", "member")
FIELD_NAMES_GROUP = ("title", "author", "genre")
FIELD_VISUAL_GROUP = ("title", "author")
FIELD_NAMES_LOG = ("id", "member", "date_out", "date_in")

DATE_FMT = "%d/%m/%Y"

Book: TypeAlias = dict[str, int | str]
Group : TypeAlias = dict[str, str]
Log: TypeAlias = dict[str, int | str | date | None]
Member: TypeAlias = str
T = TypeVar("T", Book, Log)

def make_book(id: int, title: str, author: str, genre: tuple[str, ...], purchase: str, member: str) -> Book:
    return dict(zip(FIELD_NAMES_BOOK, (id, title, author, genre, purchase, member)))
def _make_book_from_csv(id: str, title: str, author: str, genre: str, *args: str) -> Book:
    return make_book(int(id), title, author, tuple(genre.split(";")), *args)
def make_log(book: int, member: str, date_out: date, date_in: date|None) -> Log:
    return dict(zip(FIELD_NAMES_LOG, (book, member, date_out, date_in)))
def _make_log_from_csv(book: str, member: str, do: str, di: str) -> Log:
    return make_log(int(book), member, datetime.strptime(do, DATE_FMT).date(), datetime.strptime(di, DATE_FMT).date() if di else None)

def str_book(book: Book) -> Iterable[str]:
    return map(str, (book[i] for i in FIELD_NAMES_BOOK))
def str_log(log: Log) -> Iterable[str]:
    l = log.copy()
    for k in ("date_out", "date_in"):
        l[k] = "" if ((v := log[k]) is None) else v.strftime(DATE_FMT)
    return map(str, (l[i] for i in FIELD_NAMES_LOG))

def _read(filename: str, make_func: Callable[..., T]) -> Generator[T, None, None]:
    """Wrapper around csv reader to strip first header line"""
    with open(filename, encoding="utf8") as file:
        it = csv.reader(file)
        next(it) # Skip the first line as it's just headers
        yield from map(lambda i: make_func(*i), it)

def _write(filename: str, str_func: Callable[[T], Iterable[str]], fieldnames: Iterable[str], it: Iterable[T]):
    """Wrapper around csv write to add the header lines"""
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
    """Return list of books

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
	return f"#{id:0{len(str(len(books())))}d}"

def from_id(id: int) -> Book:
    """Retuns book object from a book ID"""
    for book in books():
        if book["id"] == id:
            return book
    raise KeyError("ID does not exist")
