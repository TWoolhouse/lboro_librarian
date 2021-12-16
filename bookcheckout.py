"""Bookcheckout contains functions for finding certain logs
from the database as well as being able to checkout a book
out of the library.
"""

from datetime import date, timedelta
import database.database as db

def checked_out(book: db.Book) -> bool:
    """Is the book currently checked-out with a member"""
    return bool(book["member"])

def find_log(book: db.Book) -> db.Log:
    """Find the first log which pertains to this book.

    Matches the book ID's in reverse chronological order.
    Raises ValueError if a suitable log is not found.
    """
    for log in reversed(db.logs()):
        if log["id"] == book["id"]:
            return log
    raise ValueError("Book not in logs") from None

def active_log(book: db.Book) -> db.Log:
    """Return the log for this book that is on loan

    Finds the first log and checks if it has no return date
    Raises ValueError if the book is not checked-out
    """
    if not checked_out(book):
        raise ValueError("Book is not checked-out") from None
    log = find_log(book)
    if not log["date_in"]:
        return log
    raise ValueError("Book is not checked-out") from None

def get_log(book: db.Book) -> db.Log | dict:
    """Get the first log for this book
    or an empty log if one does not exist.
    """
    try:
        return find_log(book)
    except ValueError:
        return {}

def days(book: db.Book) -> int:
    """Return number of days since the book was checked-out

    Days from the first log of the book to today
    Propagates the error from active log
    """
    dt: timedelta = date.today() - active_log(book)["date_out"]
    return abs(dt.days)

def checkout(book: db.Book, member: db.Member) -> bool:
    """Checkout the book from the library

    Edits the database to add the new member,
    creates a new log with todays date as the checkout.

    Returns False if the book is already checkout
    else return True
    """
    if checked_out(book):
        return False
    book["member"] = member
    db.members().add(member)
    db.logs().append(db.make_log(book["id"], member, date.today(), None))
    return True

if __name__ == "__main__":
    import random

    print("Checked Out:")
    assert not checked_out({"member": ""}), "Checked-out Failed"
    assert checked_out({"member": "COTW"}), "Checked-out Failed"
    print("Passed")
    print("Find Log:")
    lid = random.choice(db.logs())["id"]
    assert find_log(db.from_id(lid))["id"] == lid, "Find Log Failure"
    print("Passed")
    print("Get Log:")
    assert get_log({"id": -1}) == {}, "Get Log Found Wrong Log"
    print("Passed")
