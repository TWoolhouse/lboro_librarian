"""Searching for books and groups
using a set of search terms.
Uses generators to reduce extra time spent computing values
"""

from typing import Generator, Iterable, Iterator
import database.database as db

def is_in(book: dict[str, str], area: str, terms: Iterable[str]) -> Generator[bool, None, None]:
    """Return an Iterator of bools for each term in terms whether it is found in any of the areas of book

    area: the key in the dict of book
    Generator as to not compare every term when not all are needed.
    """
    return (term in (v if isinstance(v := book[area], str) else db.fmt_id(v)).lower() for term in terms)
def find_in(book: dict[str, str], terms: Iterable[str], *areas: str) -> bool:
    """Return a bool if all terms can be found in one of any of the areas

    areas: keys of the book dict to check.
    """
    return all(map(any, zip(*map(lambda area: is_in(book, area, terms), areas))))

def search(title: str) -> list[db.Book]:
    """Return all books with an exactly matching title"""
    return [b for b in db.books() if title == b["title"]]

def fuzzy(term: str) -> Generator[db.Book, None, None]:
    """Performs a fuzzy search over the id, title, and author

    The term is split over the spaces and provides the required terms.
    Generator of Books as they are needed.
    """
    terms = term.strip().lower().split()
    return (b for b in db.books() if find_in(b, terms, "id", "title", "author"))

def fuzzy_id(id: str) -> Iterator[db.Book]:
    """Return books with a partial id number match"""
    return (book for book in db.books() if id in str(book["id"]))

active_groups: list[db.Group] = []

def generate_group(term: str) -> list[db.Group]:
    """Return list of groups which match the search terms

    It also caches the result in the active_groups variable.
    """
    global active_groups
    terms = term.strip().lower().split()
    active_groups = [g for g in db.groups() if find_in(g, terms, "title", "author")]
    return active_groups

if __name__ == "__main__":

    print("Is In:")
    assert all(is_in({"a": "hello", "b": "world"}, "a", ["lo", "he"])), "Is In not all in one area"
    assert not any(is_in({"a": "hello", "b": "world"}, "b", ["lo", "he"])), "Is In none in one area"
    print("Passed")
    print("Find In:")
    assert find_in({"a": "hello", "b": "world", "c": "testing"}, ["lo", "he", "est"], "a", "b", "c"), "Find In did not find all"
    assert not find_in({"a": "hello", "b": "world", "c": "testing"}, ["lo", "he", "est"], "a", "b"), "Find In found some"
    print("Passed")
    print("Search:")
    orwell = search("1984")
    assert orwell, "No 1984 books found"
    print("Passed")
    print("Fuzzy:")
    assert sum(1 for _ in fuzzy("19 Orw")) == len(orwell) + 1, "Should find only 1984 and 1 animal farm"
    print("Passed")
