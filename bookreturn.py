from datetime import date, timedelta
import database as db
from bookcheckout import find_log

def submit(book: db.Book) -> int:
	"""Return the book to the library
	returns the number of days since it was checked-out"""
	log = find_log(book)
	today = log["date_in"] = date.today()
	dt: timedelta = today - log["date_out"]
	return abs(dt.days)
