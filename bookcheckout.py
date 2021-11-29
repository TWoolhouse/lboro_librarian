from datetime import date
import database as db

def checked_out(book: db.Book) -> bool:
    return bool(book["member"])

def find_log(book: db.Book) -> db.Log:
    for log in db.logs():
        if log["id"] == book["id"]:
            return log
    raise ValueError("Book not in logs") from None

def active_log(book: db.Book) -> db.Log:
    if not checked_out(book):
        raise ValueError("Book not in logs") from None
    log = find_log(book)
    if not log["date_in"]:
        return log
    raise ValueError("Book not in logs") from None

def get_log(book: db.Book) -> db.Log | dict:
    try:
        return find_log(book)
    except ValueError:
        return {}

def checkout(book: db.Book, member: str) -> bool:
    if checked_out(book):
        return False
    book["member"] = member
    db.logs().append(db.make_log(book["id"], member, date.today(), None))
    return True
