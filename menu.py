# Main entry point

import tkinter as tk
from tkinter.constants import BOTH, LEFT
import tkinter.ttk as ttk
import tkinter.font
from typing import Any, Callable, Generator, Iterable, Literal, TypeAlias, TypeVar
import bookcheckout as checkout
import booksearch as search

import database as db
from database import fmt_id

FIELD_SEARCH_BOOK = ("id", "purchase", "member", "date_out", "date_in")
FIELD_RETCHECK = ("id", "title", "author", "member", "date_out", "date_in")

WIDTH, HEIGHT = 1280, 720 # 720
FONT = 11
CHAR_SIZE = 3
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
}

T = TypeVar("T", bound=tk.Widget)
def pack(area: Literal['search', 'retcheck', 'checkout', 'return'] | tuple[Literal['search', 'retcheck', 'checkout', 'return'], ...], w: T, **params) -> T:
	if isinstance(area, str):
		area = (area,)
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
		"group": {},
		"member": "",
	}
def active_update(key: str, value: Any) -> Any:
	if value is not None:
		active["now"] = key
		active[key] = value
		STATUS_UPDATERS[key](value)
		state["retcheck"]
	return active[key]
def active_book(book: db.Book=None) -> db.Book:
	b = active_update("book", book)
	try:
		log = checkout.find_log(b)
		# log["date_member"]
	except ValueError:	pass
	return b
def active_group(group: db.Group=None) -> db.Group:
	g = active_update("group", group)
	if group is not None:
		search_book_input_cb()
		variable("bookid").set(f"{group['title']} {group['author']}")
	return g
def active_member(member: db.Member=None) -> db.Member:
	return active_update("member", member)

# --- Screen Setup --- #
def setup_screen(parent: tk.Tk) -> tk.Tk:
	parent.title("Library")

	# Set default font to be used everywhere
	font = tkinter.font.nametofont("TkDefaultFont")
	font.configure(size=FONT, family="Consolas") # Courier
	global CHAR_SIZE
	CHAR_SIZE = font.measure(" ")
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
	BG = "#28bd97"
	bar = tk.Frame(parent, width=WIDTH, height=14, bg=BG)

	OPT = {"bg":BG, "padx":PAD}

	ws: dict[str, tuple[tk.Label, tk.Label]] = state["status"]

	for key in STATUS_FIELDS:
		t = ws[key.lower()] = (tk.Label(bar, text=f"{key}:", **OPT),
			tk.Label(bar, text="V", bg=BG))
		for w in t:
			w.pack(side="left")
		update_status(key)

	bar.pack(expand=False, fill="x", side="bottom")
	return bar

def setup_side_bar(parent, height: int):
	bar = tk.Frame(parent, width=100, bg="white", height=height, relief="groove", border=1)

	for t,f in (("search",lambda: show_page("search")), ("retcheck",lambda: show_page("retcheck")), ("recommend",lambda: show_page("recommend"))):
		w = tk.Button(bar, text=ICONS[t], command=f)
		w.pack(side="top", fill="x")

	bar.pack(expand=False, fill="both", side="left")
	return bar

def setup_mainarea(parent):
	frame = state["main"] = tk.Frame(parent, bg="#CCC", relief="sunken", border=1)

	setup_main_search(frame)
	setup_main_retcheck(frame)
	# setup_main_recommend(frame)

	frame.pack(side="right", expand=True, fill="both")
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
	configure_tree(tree, ("id", "date", "member", "date", "date"))

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

	configure_tree(tree, ("id", "title", "author", "member", "date", "date"))

	# --- Right Side --- #
	rcr = ("retcheck", "checkout", "return")
	ws["title"] = pack(rcr, tk.Label(f_main, text="Checkout / Return", border=1, relief="raised"), side=tk.TOP, fill=tk.X)
	var = variable("member", tk.StringVar(f_main))
	pack(rcr, tk.Label(f_main, text="\nMember"), side=tk.TOP, fill=tk.X)
	pack(rcr, tk.Entry(f_main, textvariable=var), side=tk.TOP, fill=tk.X)

	pack("checkout", tk.Label(f_main, text="TEST"), side=tk.TOP, fill=tk.X)
	ws["btn"] = pack(rcr, tk.Button(f_main, text="Checkout / Return", command=print), side=tk.BOTTOM, fill=tk.X)

def create_search_tree(
	area: Literal['search', 'retcheck'],
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
	tree = ttk.Treeview(parent, columns=fieldnames, show="headings")
	for key in fieldnames:
		tree.heading(key, text=key.replace("_", " ").title())
	tree.bind("<<TreeviewSelect>>", tree_cb)

	for colour in COLOURS.values():
		tree.tag_configure(colour, background=colour)

	sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
	tree.configure(yscroll=sb.set)
	pack(area, sb, side=tk.RIGHT, fill=tk.Y)

	pack(area, tree, side=tk.TOP, expand=True, fill=tk.BOTH)

	return var, tree
def configure_tree(tree: ttk.Treeview, size_names: Iterable[str]):
	for col, name in enumerate(size_names, start=1):
		tree.column(f"#{col}", width=CHAR_SIZE*(2+CHAR_LEN[name]))

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
	"in": "#00ff00", # In Stock
	"out": "#ffe600", # Out on Loan
	"over": "#ff0000", # Overdue
}
def colour_lookup(book: db.Book) -> Colour:
	try:
		log = checkout.active_log(book)
		if search.old([book]):
			return COLOURS["over"]
		return COLOURS["out"]
	except ValueError:
		return COLOURS["in"]

def fmt_title(title: str) -> str:
	return title.replace("\"", "")
def fmt_genre(genres: list[str]) -> str:
	return ", ".join(genres[:3]) + (", ..." if len(genres) > 3 else "")

CHAR_LEN = {
	"date": 8,
	"member": 4,
	"id": len(fmt_id(0)),
	"title": 40,
	"author": 17,
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
	replace_tree_content(get_search_tree_side(1), FIELD_SEARCH_BOOK, ((i | checkout.get_log(i), colour_lookup(i)) for i in search.fuzzy_id(term) if {
		k: i[k] for k in db.FIELD_NAMES_GROUP # Convert to group of the book
	} == active_group()))

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
	replace_tree_content(state["retcheck"]["tree"], FIELD_RETCHECK, (checkout.get_log(b) | b for b in search.fuzzy(term)))

def retcheck_tree_cb(tree: ttk.Treeview):
	value = get_tree_selection(tree)
	if value is None:	return
	book = active_book(decompose_fmt_id(value[0]))
	fbook = fmt(book)

	ws = state["retcheck"]
	if checkout.checked_out(book):
		page = "return"
	else:
		page = "checkout"
	ws["title"]["text"] = page.title()
	ws["btn"]["text"] = f"{page.title()}: {fbook['id']} - {get_entry_term('member')}"
	show_retcheck_page(page)

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
	req = (*db.FIELD_NAMES_BOOK,)
	status_clear_not_req(req)
	for key in req[:-1]:
		update_status(key, book[key])
	update_status(req[-1], book[req[-1]] if checkout.checked_out(book) else None)

def status_clear_not_req(req: Iterable[str]):
	for key in (set(STATUS_FIELDS) - set(req)):
		update_status(key)

def update_status(key: str, value=None):
	ws = state["status"][key.lower()]
	change = (lambda w: w.pack_forget()) if value is None else (lambda w: w.pack(side="left"))
	for w in ws:
		change(w)
	if value is not None:
		try:
			value = globals()[f"fmt_{key}"](value)
		except KeyError:	pass
		ws[1]["text"] = value

STATUS_UPDATERS = {
	"book": set_status_book,
	"group": set_status_group,
	"member": lambda value: None,
}

# --- MAIN ENTRY POINT --- #
root = tk.Tk()
root.state("zoomed")
setup_screen(root)
show_page("search")
root.update()
resize(root)
root.mainloop()
