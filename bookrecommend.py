"""The recommendation system is able to continually new books for a member.

It uses the genres and global reading data to determine the best matches.
It'll return books in order of highest match and then most popular.
A 100% match means the book contains all the genres the system has
determined the member like the most, based on how many they've read
from said genres.
"""

import itertools
from collections import defaultdict
from typing import Generator, Iterable, Iterator, Sequence, TypeAlias
import database.database as db

Genre: TypeAlias = str
Recommendation: TypeAlias = tuple[db.GroupHash, int]
# A GroupHash and its matches

def engine_init() -> tuple[dict[Genre, int], dict[db.GroupHash, int], dict[Genre, set[db.GroupHash]]]:
    """Initializes the recommendation engine by creating global state.

    Returns:
        The every read genre and the count.
        The read count of every group.
        A lookup of genres to the books which contain said genre.
    """
    genres: dict[Genre, int] = defaultdict(int)
    read: dict[db.GroupHash, int] = defaultdict(int)
    genre_groups: dict[Genre, set[db.GroupHash]] = defaultdict(set)

    for log in reversed(db.logs()):
        book = db.from_id(log["id"])
        read[db.hash_group(book)] += 1
        for genre in book["genre"]:
            genres[genre] += 1

    for gh, g in db.group_table().items():
        for genre in g["genre"]:
            genre_groups[genre].add(gh)

    return genres, read, genre_groups

genres, read, genre_groups = engine_init()

def engine_update():
    """Update the global state of the recommendation engine.

    Required after the database has been updated.
    """
    global genres, read, genre_groups
    genres, read, genre_groups = engine_init()

def recommendation(member: db.Member) -> tuple[dict[Genre, int], Iterable[Genre], Generator[Recommendation, None, None]]:
    """Generates Recommendations for a member.

    Returns:
        The read genre counts - Number of times each genre was read by this member.
        An Iterable of the top genres used in the recommendation system.
        The Recommendation Generator object.
    """
    member_genres: dict[Genre, int] = defaultdict(int)
    member_books = [db.from_id(log["id"]) | log for log in reversed(db.logs()) if log["member"] == member]

    for book in member_books:
        for genre in book["genre"]:
            member_genres[genre] += 1

    member_read = {db.hash_group(book) for book in member_books}

    genre_counts: dict[int, list[Genre]] = defaultdict(list)
    for genre, count in member_genres.items():
        genre_counts[count].append(genre)

    counts = sorted(genre_counts, reverse=True)

    top_genre_groups = [genre_counts[count] for count, _ in zip(counts, range(5))]
    top_genres = [j for i in top_genre_groups for j in i]

    return member_genres, top_genres, (gh for gh in generate_recommendations(top_genre_groups) if gh[0] not in member_read)

def generate_recommendations(genre_seq: Sequence[Sequence[Genre]]) -> Generator[Recommendation, None, None]:
    """Generates Recommendations from groups of genres.

    Produces unique Book Group recommendations using the genres,
    yielding the highest matching to the genres and most read first.
    """
    done: set[db.GroupHash] = {None}
    for perm_group in combine_permutations(genre_seq):
        head, tail = perm_group[:-1], perm_group[-1]
        genres = {g for gs in head for g in gs} # Flattern the genre groups
        iterators = [compatible_books(genres.union(g)) for g in tail]

        # Evenly exhausts the iterators as so no genre combination gets priority
        for groups in (filter(None, tup) for tup in itertools.zip_longest(*iterators)):
            # sorted by number of global reads
            for group, matches in sorted(groups, key=lambda x: read[x[0]], reverse=True):
                if group not in done:
                    done.add(group)
                    yield (group, matches)

def combine_permutations(genres_seq: Sequence[Sequence[Genre]]) -> Generator[Sequence[Sequence[Genre] | Iterator[Sequence[Genre]]], None, None]:
    """Generates combination groups from genres in decreasing size order.

    Yields a single combination e.g. [("Fantasy", "Classics"), ("Children"), <Combinations>]
    where combinations is an iterator of different combinations (all the same length).
    """
    # Yield nothing to make it a generator when we've reached the end of the sequence
    if not genres_seq:	return (yield from ())
    genres = genres_seq[0]
    genres_sub = genres_seq[1:]

    for permutations in permutation_groups(genres):
        for perm in permutations:
            for sub_perms in combine_permutations(genres_sub):
                yield (perm, *sub_perms)
    yield from ((i,) for i in permutation_groups(genres))

def permutation_groups(genres: Sequence[Genre]) -> Generator[Iterator[Sequence[Genre]], None, None]:
    """Generates all different length Iterators of combinations.

    In decreasing size, creates the combinations of genres,
    until its just single genres.
    """
    yield iter((genres,))
    for size in reversed(range(1, len(genres))):
        yield itertools.combinations(genres, size)

def compatible_books(genres: Sequence[Genre]) -> Generator[Recommendation, None, None]:
    """Generates Recommendations which have all of the genres.

    A recommendation has the GroupHash and the number of genres.
    The number of genres is important for match %.
    """
    it = iter(genres)
    size = len(genres)
    return ((i, size) for i in generate_compatible(it, genre_groups[next(it)].copy()))

def generate_compatible(genres: Iterator[Genre], compat: set[db.GroupHash]) -> Iterable[db.GroupHash]:
    """Return an Iterable of GroupHashes in which
    a group must contain every genere in the Iterator genres
    """
    try:
        # Take intersection of previous BookGroups and this genres
        compat &= genre_groups[next(genres)]
        return generate_compatible(genres, compat)
    except StopIteration:
        gtable = db.group_table()
        # Sort by the most read
        return sorted(compat, key=lambda gh: (read[gh], gtable[gh]["title"]), reverse=True)
