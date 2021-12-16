import itertools
from collections import defaultdict
from typing import Generator, Iterable, Iterator, Sequence, TypeAlias
import database.database as db

Genre: TypeAlias = str
Recommendation: TypeAlias = tuple[db.GroupHash, int]

def engine_init() -> tuple[dict[Genre, int], dict[int, int], dict[Genre, set[db.GroupHash]]]:
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

SizeChange: TypeAlias = tuple[int]
SIZE_CHANGE: SizeChange = (1,)

def generate_recommendations(genre_seq: Sequence[Sequence[Genre]]) -> Generator[Recommendation, None, None]:
    done: set[db.GroupHash] = {None}
    for perm_group in combine_permutations(genre_seq):
        head, tail = perm_group[:-1], perm_group[-1]
        genres = {g for gs in head for g in gs}
        iterators = [compatible_books(genres.union(g)) for g in tail]
        for groups in (filter(None, tup) for tup in itertools.zip_longest(*iterators)):
            x = sorted(groups, key=lambda x: read[x[0]], reverse=True)
            for group, matches in x:
                if group not in done:
                    done.add(group)
                    yield (group, matches)

def combine_permutations(genres_seq: Sequence[Sequence[Genre]]) -> Generator[Sequence[Sequence[Genre] | Iterator[Sequence[Genre]]], None, None]:
    if not genres_seq:	return (yield from ())
    genres = genres_seq[0]
    genres_sub = genres_seq[1:]

    for permutations in permutation_groups(genres):
        for perm in permutations:
            for sub_perms in combine_permutations(genres_sub):
                yield (perm, *sub_perms)
    yield from ((i,) for i in permutation_groups(genres))

def permutation_groups(genres: Sequence[Genre]) -> Generator[Iterator[Sequence[Genre]], None, None]:
    yield iter((genres,))
    for size in reversed(range(1, len(genres))):
        yield itertools.combinations(genres, size)

def compatible_books(genres: Sequence[Genre]):
    it = iter(genres)
    size = len(genres)
    return ((i, size) for i in generate_compatible(it, genre_groups[next(it)].copy()))

def generate_compatible(genres: Iterator[Genre], compat: set[db.GroupHash]) -> Iterable[db.GroupHash]:
    try:
        compat &= genre_groups[next(genres)]
        return generate_compatible(genres, compat)
    except StopIteration:
        gtable = db.group_table()
        return sorted(compat, key=lambda gh: (read[gh], gtable[gh]["title"]), reverse=True)
