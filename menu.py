# Main entry point

import string
from collections import defaultdict
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font
from typing import Any, Callable, Generator, Iterable, Iterator, Literal, TypeAlias, TypeVar

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import booksearch as search
import bookcheckout as checkout
import bookreturn as breturn
import bookrecommend as recommend

import database.database as db
from database.database import Member, fmt_id

FIELD_SEARCH_BOOK = ("id", "purchase", "member", "date_out", "date_in")
FIELD_RETCHECK = ("id", "title", "author", "member", "date_out", "date_in")
FIELD_MEMBER_BOOK = ("id", "days", "title")
FIELD_MEMBER = ("member",)
FIELD_REC = ("match", "reads", "title", "author")

WIDTH, HEIGHT = 1280, 720 # 720
FONT = 11
CHAR_SIZE = 1
CHAR_HEIGHT = 1
TITLE = "Library"

ICONS = {
    "search": "🔎",
    "retcheck": "⇌",
    "recommend": "🫂",
}

# Global State of the GUI
state: dict[str, Any] = {
    "var": {},
    "pack": {
        "search": {},
        "retcheck": {},
        "checkout": {},
        "return": {},
        "recommend": {},
    },
    "status": {},
    "search": {},
    "retcheck": {},
    "recommend": {},
    "plot": {},
}

T = TypeVar("T", bound=tk.Widget)
def pack(area: Literal['search', 'retcheck', 'checkout', 'return', 'recommend'] | tuple[Literal['search', 'retcheck', 'checkout', 'return', 'recommend'], ...] | None, w: T, **params) -> T:
    if isinstance(area, str):
        area = (area,)
    elif area is None:
        w.pack(**params)
        return w
    for a in area:
        state["pack"][a][w] = params
    return w

V = TypeVar("V", bound=tk.Variable)
def variable(name: str, var: V=None) -> V:
    if var is not None:
        state["var"][name] = var
    return state["var"][name]

# Global State of Active Selected Components
active: dict[str, str | db.Book | db.Group | db.Member] = {
    "now": "",
    "book": {},
    "group": {"title": "", "author": ""},
    "member": "",
}
active_callbacks: dict[str, list[Callable[[Any], Any]]] = {
    "book": [],
    "group": [],
    "member": [],
}
def on_cb(key: Literal['book', 'group', 'member'], func: Callable[[Any], Any]):
    active_callbacks[key].append(func)
def active_update(key: str, value: Any) -> Any:
    if value is not None:
        active["now"] = key
        if (b := active[key]) == value:
            return b
        active[key] = value
        STATUS_UPDATERS[key](value)
        for cb in active_callbacks[key]:
            cb(value)
    return active[key]
def active_book(book: db.Book=None) -> db.Book:
    return active_update("book", book)
def active_group(group: db.Group=None) -> db.Group:
    return active_update("group", group)
def active_member(member: db.Member=None) -> db.Member:
    return active_update("member", member)

# --- Screen Setup --- #
def setup_screen(parent: tk.Tk) -> tk.Tk:
    parent.title("Library")

    # Set default font to be used everywhere
    font = tkinter.font.nametofont("TkDefaultFont")
    font.configure(size=FONT, family="Consolas") # Courier
    global CHAR_SIZE, CHAR_HEIGHT
    CHAR_SIZE = font.measure(" ")
    CHAR_HEIGHT = font.metrics("linespace")
    parent.option_add("*Font", font)

    resize_cb = lambda e: resize(e.widget)
    parent.bind("<Configure>", resize_cb)
    parent.bind("<<Maximize>>", resize_cb)
    parent.bind("<<Minimize>>", resize_cb)

    # Dynamic width & height
    width, height = WIDTH, HEIGHT

    height -= setup_status_bar(parent)["height"]
    width -= setup_side_bar(parent, height).winfo_width()

    setup_mainarea(parent)

    parent.geometry(f"{WIDTH}x{HEIGHT}")
    return parent

STATUS_FIELDS = ("ID", "Title", "Author", "Genre", "Member", "Purchase")
def setup_status_bar(parent: tk.Misc) -> tk.Widget:
    PAD = 4
    BG = "#43b8bf"
    bar = tk.Frame(parent, width=WIDTH, height=6+CHAR_HEIGHT, bg=BG)
    bar.pack_propagate(False)

    OPT = {"bg":BG, "padx":PAD}

    ws: dict[str, tuple[tk.Label, tk.Label]] = state["status"]

    for key in STATUS_FIELDS:
        t = ws[key.lower()] = (tk.Label(bar, text=f"{key}:", **OPT),
            tk.Label(bar, text="V", bg=BG))
        for w in t:
            w.pack(side=tk.LEFT)
        update_status(key)

    bar.pack(expand=False, fill=tk.X, side=tk.BOTTOM)
    return bar

def setup_side_bar(parent, height: int):
    bar = tk.Frame(parent, width=100, bg="white", height=height, relief="groove", border=1)

    for t,f in (("search",lambda: show_page("search")), ("retcheck",lambda: show_page("retcheck")), ("recommend",lambda: show_page("recommend"))):
        w = tk.Button(bar, text=ICONS[t], command=f)
        w.pack(side=tk.TOP, fill=tk.X)

    bar.pack(expand=False, fill=tk.BOTH, side=tk.LEFT)
    return bar

def setup_mainarea(parent):
    frame = state["main"] = tk.Frame(parent, bg="#CCC", relief="sunken", border=1)

    setup_main_search(frame)
    setup_main_retcheck(frame)
    setup_main_recommend(frame)

    frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
    return frame

def setup_main_search(parent: tk.Frame):
    ws: dict[str, Any] = {
        "tree": [],
        # "checkout": tk.Button(),
    }
    state["search"] = ws

    frames = [tk.Frame(parent, relief=tk.GROOVE, border=1) for _ in range(2)]
    for f in frames:
        pack("search", f, side=tk.LEFT, expand=True, fill=tk.BOTH)
        f.pack_propagate(False)

    var, tree = create_search_tree("search",
        frames[0],
        lambda a,b,c: search_group_input_cb(),
        lambda e: search_group_list_cb(e.widget),
        "Book Search",
        "group",
        db.FIELD_VISUAL_GROUP,
    )
    ws["tree"].append(tree)
    # Set var to empty to execute the callback and fill the treeview
    var.set("")

    var, tree = create_search_tree("search",
        frames[1],
        lambda a,b,c: search_book_input_cb(),
        lambda e: search_book_list_cb(e.widget),
        "Book ID Search",
        "book",
        FIELD_SEARCH_BOOK,
    )
    ws["tree"].append(tree)
    var.set("")

    ws["checkout"] = pack("search", tk.Button(frames[1], text="Checkout / Return", command=search_to_retcheck, state=tk.DISABLED), side=tk.TOP)
    configure_tree(tree, (("id", False), "date", "member", "date", "date"))

def setup_main_retcheck(parent: tk.Frame):
    ws: dict[str, Any] = {
        # "main": tk.Frame,
    }
    state["retcheck"] = ws
    f_search, f_main = frames = [tk.Frame(parent, relief=tk.GROOVE, border=1) for _ in range(2)]
    ws["main"] = f_main
    for frame in frames:
        pack("retcheck", frame, side=tk.LEFT, expand=True, fill=tk.BOTH)
        # frame.pack_propagate(False)

    # --- Left Side --- #
    var, tree = create_search_tree(
        "retcheck",
        f_search,
        lambda a,b,c: retcheck_input_cb(),
        lambda e: retcheck_tree_cb(e.widget),
        "Book ID Search",
        "bookid",
        FIELD_RETCHECK,
    )
    ws["tree"] = tree
    # Set var to empty to execute the callback and fill the treeview
    var.set("")
    on_cb("group", lambda group: variable("bookid").set(f"{group['title']} {group['author']}"))

    configure_tree(tree, ("id", ("title", True), ("author", True), "member", "date", "date"), False)

    # --- Right Side --- #
    rcr = ("retcheck", "checkout", "return")
    ws["title"] = pack(rcr, tk.Label(f_main, text="Checkout / Return", relief="raised", border=1), pady=3, side=tk.TOP, fill=tk.X)

    var, tree = create_search_tree(
        rcr,
        f_main,
        lambda a,b,c: retcheck_member_cb(),
        lambda e: retcheck_members_list_cb(e.widget),
        "Member",
        "member",
        FIELD_MEMBER,
    )
    configure_tree(tree, FIELD_MEMBER)
    ws["mtree"] = tree

    tree, _ = create_tree(rcr, f_main, lambda e: retcheck_member_list_cb(e.widget), FIELD_MEMBER_BOOK)
    configure_tree(tree, ("id", "days", ("stitle", True)), False)
    ws["mbtree"] = tree
    on_cb("member", lambda member: variable("member").set(member))

    ws["btn"] = pack(rcr, tk.Button(f_main, text=fmt_retcheck_btn("Checkout / Return"), command=retcheck_btn, state=tk.DISABLED), side=tk.BOTTOM, fill=tk.X)
    retcheck_member_cb()

def setup_main_recommend(parent: tk.Frame):
    ws: dict[str, Any] = {
        "plot": {},
        "data": {
            "member": "",
            "generator": None,
            "memory": [],
            "genres": [],
            "genre_count": {},
        },
    }
    state["recommend"] = ws

    notebook = pack("recommend", ttk.Notebook(parent), side=tk.TOP, expand=True, fill=tk.BOTH)

    tab_table, tab_graph = (pack(None, tk.Frame(notebook), expand=True, fill=tk.BOTH, side=tk.TOP) for _ in range(2))

    # Graph
    notebook.add(tab_graph, text="Graph 📈")
    fig, canvas = setup_figure(tab_graph)
    ws["plot"]["canvas"] = canvas
    pack(None, canvas.get_tk_widget(), side=tk.TOP, expand=True, fill=tk.BOTH)
    ax: plt.Axes = fig.add_subplot(1, 2, 1)
    ws["plot"]["match"] = ax
    tab_plot_matches(ax, {101: 0, -1: 0})

    ax = fig.add_subplot(1, 2, 2)
    ws["plot"]["book_reads"] = ax
    tab_plot_reads(ax, {"Book Title": 0})

    # Table
    notebook.add(tab_table, text="Table 📋")
    tree, _ = create_tree(None, tab_table, lambda e: tab_table_cb(e.widget) , FIELD_REC)
    ws["tree"] = tree
    configure_tree(tree, (("match", False), ("reads", False), "title", "author"))

on_cb("member", lambda member: variable("recommend").set(member))

def setup_figure(parent: tk.Frame):
    fig = Figure(figsize=(24, 24), dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=parent)  # A tk.DrawingArea.

    toolbar = NavigationToolbar2Tk(canvas, parent, pack_toolbar=False)
    toolbar.update()

    canvas.mpl_connect("key_press_event", key_press_handler)
    return fig, canvas

def create_search_tree(
    area: str | Iterable[str],
    parent: tk.Frame,
    entry_cb: Callable[[Any, Any, Any], Any],
    tree_cb: Callable[[tk.Event], Any],
    label_text: str,
    var_name: str,
    fieldnames: Iterable[str],
) -> tuple[tk.StringVar, ttk.Treeview]:
    pack(area, tk.Label(parent, text=label_text), side=tk.TOP, fill=tk.X)
    var = variable(var_name, tk.StringVar(parent))
    var.trace_add("write", entry_cb)
    pack(area, tk.Entry(parent, textvariable=var), side=tk.TOP, fill=tk.X)
    tree, _ = create_tree(area, parent, tree_cb, fieldnames)
    return var, tree

def create_tree(area: str | Iterable[str], parent: tk.Frame, tree_cb: Callable[[tk.Event], Any], fieldnames: Iterable[str]) -> tuple[ttk.Treeview, ttk.Scrollbar]:
    frame = tk.Frame(parent)
    tree = ttk.Treeview(frame, columns=fieldnames, show="headings")
    for key in fieldnames:
        tree.heading(key, text=key.replace("_", " ").title())
    tree.bind("<<TreeviewSelect>>", tree_cb)

    for colour in COLOURS.values():
        tree.tag_configure(colour, background=colour)

    sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=sb.set)
    pack(area, sb, side=tk.RIGHT, fill=tk.Y)

    pack(area, tree, side=tk.TOP, expand=True, fill=tk.BOTH)
    pack(area, frame, side=tk.TOP, expand=True, fill=tk.BOTH)
    return tree, sb

def configure_tree(tree: ttk.Treeview, size_names: Iterable[str | tuple[str, bool]], stretch=True):
    for col, sn in enumerate(size_names, start=1):
        if isinstance(sn, str):
            name, strtch = sn, stretch
        else:
            name, strtch = sn
        width = CHAR_SIZE * (2 + CHAR_LEN[name])
        tree.column(f"#{col}", stretch=strtch, width=width, minwidth=width)

# --- Tabs --- #

def iter_rec() -> Generator[Recommendation, None, None]:
    data = state["recommend"]["data"]
    member = active_member()
    if data["member"] != member:
        data["member"] = member
        data["genre_count"], data["genres"], gen = recommend.recommendation(member)
        data["generator"] = gen
        memory = data["memory"] = []
    else:
        gen = data["generator"]
        memory = data["memory"]

    yield from memory
    for item in gen:
        memory.append(item)
        yield item

def rec_size(size: int) -> Iterator[Recommendation]:
    for tup, _ in zip(iter_rec(), range(size)):
        yield tup

def split_name(name: str) -> str:
    out = ""
    while len(name) > 15:
        ind = name.find(" ", 15)
        if ind == -1:
            ind = 15
        out += name[:ind] + "\n"
        name = name[ind:]
    out += name
    return out

def plot_matches_data(data: Iterator[Recommendation]):
    matches: dict[float, int] = defaultdict(int)
    for _, percent in data:
        matches[percent] += 1
    total_genres = len(state["recommend"]["data"]["genres"])
    return {k / total_genres * 100 : v for k,v in matches.items()}

def tab_plots_new(member: Member):
    if not db.valid_member(member) or state["recommend"]["data"]["member"] == member:	return

    plots = state["recommend"]["plot"]
    tab_plot_matches(plots["match"], plot_matches_data(rec_size(100)))
    tab_plot_reads(plots["book_reads"], state["recommend"]["data"]["genre_count"])
    plots["canvas"].draw()

    total_genres = len(state["recommend"]["data"]["genres"])
    gtable = db.group_table()
    replace_tree_content(state["recommend"]["tree"], FIELD_REC, (
        gtable[gh] | {"match": per / total_genres * 100, "reads": recommend.read[gh]} for gh, per in rec_size(100)
    ))

on_cb("member", tab_plots_new)

def tab_plot_matches(ax: plt.Axes, data: dict[float, int]):
    ax.clear()
    if data:
        ax.plot(*zip(*data.items()), "bo-")
    ax.set_title(f"{active_member() or 'No Member Selected'}\nNumber of Books with Match Percentage")
    ax.set_xlabel("Match %")
    ax.set_ylabel("Count")
    ax.invert_xaxis()
    ax.set_xbound(0, 100)
    ax.set_ybound(0, max(1, max(data.values() if data else (0,))+1))

def tab_plot_reads(ax: plt.Axes, data: dict[str, int]):
    ax.clear()
    minsize = 0
    while len(data) > 25:
        minsize += 1
        data = {k:v for k,v in data.items() if v > minsize}
    if data:
        ax.bar(*zip(*data.items()))
    ax.tick_params("x", labelrotation=75, labelsize=10)
    ax.set_title(f"{active_member() or 'No Member Selected'}\nNumber of Books Read per Genre")
    ax.set_xlabel("Genres")
    ax.set_ylabel("Read Books")
    ax.set_ybound(0, max(1, max(data.values() if data else (0,))))

def tab_table_cb(tree: ttk.Treeview):
    value = get_tree_selection(tree)
    if value is None:	return
    active_group(db.group_table()[db.hash_group(dict(zip(FIELD_REC, value)))])

# --- Show Page --- #
def show(parent: tk.Widget, children: dict[tk.Widget, dict[str, Any]]):
    for child in parent.pack_slaves():
        child.pack_forget()
    for w, p in children.items():
        w.pack(**p)

def show_page(title: Literal['search', 'retcheck', 'recommend']):
    show(state["main"], state["pack"][title])
    root.title(f"{TITLE} - {title.replace('retcheck', 'Checkout / Return').title()} {ICONS[title.lower()]}")

def show_retcheck_page(title: Literal['checkout', 'return']):
    show(state["retcheck"]["main"], state["pack"][title])
    root.title(f"{TITLE} - {title.title()} {ICONS['retcheck']}")

# --- Data Type Display Formats --- #
Colour: TypeAlias = str
COLOURS: dict[str, Colour] = {
    "in": "#b8ffcb", # In Stock
    "out": "#fff385", # Out on Loan
    "over": "#ff6b6b", # Overdue
}
def colour_lookup(book: db.Book) -> Colour:
    try:
        log = checkout.active_log(book)
        if checkout.days(book) > 60:
            return COLOURS["over"]
        return COLOURS["out"]
    except ValueError:
        return COLOURS["in"]

def fmt_title(title: str) -> str:
    return title.replace("\"", "")
def fmt_member(member: db.Member) -> str:
    return member.upper()
def fmt_genre(genres: list[str]) -> str:
    return ", ".join(genres[:3]) + (", ..." if len(genres) > 3 else "")
def fmt_match(match: float) -> str:
    return f"{match:.2f}%"

def fmt_retcheck_btn(text: str) -> str:
    return f"{text.strip(): ^{20+len(fmt_id(0))}}"

CHAR_LEN = {
    "date": 10,
    "member": 6,
    "id": len(fmt_id(0)),
    "title": 40,
    "author": 17,
    "days": 4,
    "stitle": 10,
    "match": 8,
    "reads": 9,
}

def fmt_field(key: str, value: Any) -> str:
    return globals().get(f"fmt_{key}", str)(value)
def fmt(obj: dict[str, Any]) -> dict[str, str]:
    return {k: fmt_field(k,v) for k,v in obj.items()}

def decompose_fmt_id(id: str) -> db.Book:
    return db.from_id(int(id[1:]))

# --- Generic Getters --- #
def get_entry_term(name: str) -> str:
    return variable(name).get().strip()

def replace_tree_content(tree: ttk.Treeview, fields: Iterable[str], items: Iterable[dict[str, Any] | tuple[dict[str, Any], str]]):
    tree.delete(*tree.get_children())
    for item in items:
        if isinstance(item, dict):
            v = fmt(item)
            tree.insert("", tk.END, values=tuple(v.get(k, "") for k in fields))
        else: # tuple[row, colour]
            v = fmt(item[0])
            iid = tree.insert("", tk.END, values=tuple(v.get(k, "") for k in fields))
            tree.item(iid, tags=item[1])

def get_tree_selection(tree: ttk.Treeview) -> list[str] | None:
    try:
        return tree.item(tree.selection()[0])["values"]
    except IndexError:	return

# --- Search Page Functions & Callbacks --- #
def get_search_tree_side(side: int) -> ttk.Treeview:
    return state["search"]["tree"][side]

def search_group_input_cb():
    term = get_entry_term("group")
    tree = get_search_tree_side(0)
    replace_tree_content(tree, db.FIELD_VISUAL_GROUP, search.generate_group(term))

def search_group_list_cb(tree: ttk.Treeview):
    try:
        value: list[str] = list(map(str, tree.item(tree.selection()[0])["values"]))
    except IndexError:	return
    for group in search.active_groups:
        v = [fmt_field(k, group[k]) for k in db.FIELD_VISUAL_GROUP]
        if v == value:
            return active_group(group)

def search_book_input_cb():
    term = get_entry_term("book")
    group_hash = db.hash_group(active_group())
    replace_tree_content(get_search_tree_side(1), FIELD_SEARCH_BOOK, ((i | checkout.get_log(i), colour_lookup(i)) for i in search.fuzzy_id(term) if \
        db.hash_group(i) == group_hash))
on_cb("group", lambda group: search_book_input_cb())

def search_book_list_cb(tree: ttk.Treeview):
    value = get_tree_selection(tree)
    if value is None:	return
    btn: tk.Button = state["search"]["checkout"]
    book = active_book(decompose_fmt_id(value[FIELD_SEARCH_BOOK.index("id")]))
    fbook = fmt(book)
    show = f"{fbook['id']} - {fbook['title']}"
    if checkout.checked_out(book):
        btn["text"] = f"Return: {show}"
    else:
        btn["text"] = f"Checkout: {show}"
    btn["state"] = tk.NORMAL

# --- Checkout Return Page --- #
def search_to_retcheck():
    book = active_book()
    variable("bookid").set(f"{book['title']} {book['author']}")
    tree: ttk.Treeview = state["retcheck"]["tree"]
    fid = fmt_id(book["id"])
    for id in tree.get_children():
        if tree.item(id, "values")[0] == fid:
            tree.see(id)
            tree.selection_set(id)
            break
    show_page("retcheck")

def retcheck_input_cb():
    term: str = get_entry_term("bookid")
    replace_tree_content(state["retcheck"]["tree"], FIELD_RETCHECK, ((b | checkout.get_log(b), colour_lookup(b)) for b in search.fuzzy(term)))

def retcheck_tree_cb(tree: ttk.Treeview):
    value = get_tree_selection(tree)
    if value is None:	return
    book = active_book(decompose_fmt_id(value[0]))

def retcheck_member_cb():
    var: tk.StringVar = variable("member")
    term: str = var.get()
    original = term
    term = term.upper()
    if len(term) > 4:
        term = term[:4]
    for char in term:
        if char not in string.ascii_uppercase:
            term = term.replace(char, "")
    if original != term:
        var.set(term)
    active_member(term)

    tree = state["retcheck"]["mbtree"]
    if db.valid_member(term):
        replace_tree_content(tree, FIELD_MEMBER_BOOK, ((b | checkout.get_log(b) | {"days": checkout.days(b)}, colour_lookup(b))
            for b in db.books() if b["member"] == term
        ))
    else:
        replace_tree_content(tree, [], [])

    tree: ttk.Treeview = state["retcheck"]["mtree"]
    if not (sel := get_tree_selection(tree)) or sel[0] != term:
        replace_tree_content(tree, FIELD_MEMBER, ({"member":m} for m in sorted(db.members()) if term in m))

def retcheck_members_list_cb(tree: ttk.Treeview):
    value = get_tree_selection(tree)
    if value is None:	return
    variable("member").set(value[0])

def retcheck_member_list_cb(tree: ttk.Treeview):
    value = get_tree_selection(tree)
    if value is None:	return
    book = decompose_fmt_id(value[0])
    if active_book() == book:
        return
    active_book(book)
    for iid in tree.get_children():
        if tree.item(iid, "values")[0] == value[0]:
            tree.selection_set(iid)
            tree.see(iid)
            return

def retcheck_title_update(book: db.Book):
    if checkout.checked_out(book):
        page = "return"
        variable("member").set(book["member"])
    else:
        page = "checkout"
    state["retcheck"]["title"]["text"] = page.title()
on_cb("book", retcheck_title_update)

def retcheck_btn_update():
    btn: tk.Button = state["retcheck"]["btn"]
    member = active_member()
    book = active_book()
    if not book:
        btn["text"] = fmt_retcheck_btn("Checkout / Return")
        btn["state"] = tk.DISABLED
    elif len(member) == 4:
        btn["state"] = tk.NORMAL
        btn["text"] = fmt_retcheck_btn(f"{state['retcheck']['title']['text']}: {fmt_id(book['id'])} - {member}")
    else:
        btn["state"] = tk.DISABLED
        btn["text"] = fmt_retcheck_btn(f"{state['retcheck']['title']['text']}: {fmt_id(book['id'])}")
_retcheck_btn_update_cb = lambda any: retcheck_btn_update()
on_cb("book", _retcheck_btn_update_cb)
on_cb("member", _retcheck_btn_update_cb)

def retcheck_btn():
    book = active_book()
    if checkout.checked_out(book):
        breturn.submit(book)
    else:
        checkout.checkout(book, active_member())
    db.save()
    db.checkout()
    recommend.engine_update()

    retcheck_input_cb()
    tree: ttk.Treeview = state["retcheck"]["tree"]
    fid = fmt(book)["id"]
    for child in tree.get_children():
        if tree.item(child, "values")[0] == fid:
            tree.selection_set(child)
            tree.see(child)
            break

def resize(wig):
    if wig is not root:
        return
    search_group_input_cb()

# --- Updating Status Bar --- #
def set_status_group(group: db.Group):
    req = db.FIELD_NAMES_GROUP
    status_clear_not_req(req)
    for key in req:
        update_status(key, group[key])

def set_status_book(book: db.Book):
    req = db.FIELD_NAMES_BOOK
    status_clear_not_req(req)
    for key in req[:-1]:
        update_status(key, book[key])
    update_status(req[-1], book[req[-1]] if checkout.checked_out(book) else None)

def set_status_member(member: db.Member):
    update_status("member", member)

def status_clear_not_req(req: Iterable[str]):
    for key in (set(STATUS_FIELDS) - set(req)):
        update_status(key)

def update_status(key: str, value=None):
    swap = key in ("member",)
    ws: tuple[tk.Label, tk.Label] = state["status"][key.lower()]
    change = (lambda w: w.pack_forget()) if value is None else (lambda w: w.pack(side=tk.RIGHT if swap else tk.LEFT))
    for w in (reversed(ws) if swap else ws):
        change(w)
    if value is not None:
        try:
            value = globals()[f"fmt_{key}"](value)
        except KeyError:	pass
        ws[1]["text"] = value

STATUS_UPDATERS = {
    "book": set_status_book,
    "group": set_status_group,
    "member": set_status_member	,
}

# --- MAIN ENTRY POINT --- #
root = tk.Tk()
root.state("zoomed")
setup_screen(root)
show_page("search")
root.update()
resize(root)
root.mainloop()
