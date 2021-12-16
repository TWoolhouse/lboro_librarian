"""The module handles returning a book back to the library"""

from datetime import date
import database.database as db
from bookcheckout import active_log, days

def submit(book: db.Book) -> int:
    """Return the book to the library
    returns the number of days since it was checked-out

    Edits the logs to add today's date as the return date
    Edits the book to remove the member from the database
    Will propegate the active_log error
    """
    log = active_log(book)
    log["date_in"] = date.today()
    book["member"] = ""
    return days(book)
