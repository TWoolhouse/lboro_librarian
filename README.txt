Requires: Python 3.10 (Due to TypeAlias) & Matplotlib 3.5.0. Run menu.py
Usage:
	The 3 tabs on the side are search, checkout / return, and recommend respectively.

	The blue bar located at the bottom is used to see the currently selected item,
	which could be a book, a book group (a book without an ID), or a member.

	Books highlighted with Green are in stock.
	Yellow means they are on loan.
	Red is forbooks overdue (60 days).

	The books will show the current / previous member who has taken the book
	out as well as the dates for such.

	On the checkout / return screen, selecting a book will allow you to take it
	out by inputting or selecting a user. Or return it from the user who has currently
	taken it out.

	When a member has been selected (or inputted) in the checkout / return screen,
	the recommendation window will update with the results.

	Recommendation has two windows, the graph and the table. A book selected on the
	table window can be easily checked-out from the checkout tab.


Recommendation Engine:
Firstly, it undergoes an initialization phase, to parse the statistics on the
entire database using the logfile. When a user wants a recommendation, it takes
the most read genres of that member and returns all books which contain those
genres with the most read books first. After those, it goes through the combinations
of genres, removing the ones read the least first and finding the books that
match the genres remaining. It recursively backtracks until it is only searching
single genres. This allows a match percentage to be calculated for each book.

Docstrings: I have used Python's type hints to describe the data type taken by
each parameter in a function as well as document it's return type.

Testing: Modules can be tested by running them individually and will pass as
long as no assertions are hit nor any runtime errors are produced.
