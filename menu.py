# Main entry point

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font
from typing import Any, Callable, Generator, Iterable, Literal, TypeAlias, TypeVar
import bookcheckout as checkout
import booksearch as search

import database as db

FIELD_SEARCH_BOOK = ("id", "purchase", "member", "date_out", "date_in")

WIDTH, HEIGHT = 1280, 720 # 720
FONT = 11
CHAR_SIZE = 3
TITLE = "Library"

ICONS = {
	"search": "🔎",
	"checkout": "⇌",
	"recommend": "🫂",
}

# Global State of the GUI
state: dict[str, Any] = {
	"var": {},
	"pack": {
		"search": {},
		"checkout": {},
		"recommend": {},
	},
	"status": {},
	"search": {},
}

T = TypeVar("T", bound=tk.Widget)
def pack(area: Literal['search'], w: T, **params) -> T:
	state["pack"][area][w] = params
	return w
def name(area: Literal['search'], name: str, w: T=None, **params) -> T:
	if w is not None:
		state[area][name] = pack(area, w, **params)
	return state[area][name]

V = TypeVar("V", bound=tk.Variable)
def variable(name: str, var: V=None) -> V:
	if var is not None:
		state["var"][name] = var
	return state["var"][name]

# Global State of Active Selected Components
active: dict[str, db.Book | db.Group | db.Member] = {
		"book": {},
		"group": {},
		"member": "",
	}
def active_update(key: str, value: Any) -> Any:
	if value is not None:
		active[key] = value
		STATUS_UPDATERS[key](value)
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
		search_book_input_cb(None, None, None)
	return g
def active_member(member: db.Member=None) -> db.Member:
	return active_update("member", member)

# --- Screen Setup --- #
def setup_screen(parent: tk.Tk) -> tk.Tk:
	parent.title("Library")

	# Set default font to be used everywhere
	font = tkinter.font.nametofont("TkDefaultFont")
	font.configure(size=FONT, family="Consolas") # Courier
	print(font.actual("family"))
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

	for t,f in (("search",lambda: show_page("search")), ("checkout",lambda: show_page("checkout")), ("recommend",lambda: show_page("recommend"))):
		w = tk.Button(bar, text=ICONS[t], command=f)
		w.pack(side="top", fill="x")

	bar.pack(expand=False, fill="both", side="left")
	return bar

def setup_mainarea(parent):
	frame = state["main"] = tk.Frame(parent, bg="#CCC", relief="sunken", border=1)

	# --- Search Tab --- #:
	ws = state["search"] = {
		"tree": [],
	}
	for parent_frame, input_cb, tree_cb, text, var, fieldnames in zip(
		[tk.Frame(frame, relief="groove", border=1) for _ in range(2)],
		(search_group_input_cb, search_book_input_cb),
		(search_group_list_cb, search_book_list_cb),
		("Book Search", "Book ID Search"),
		("group", "book"),
		(db.FIELD_VISUAL_GROUP, FIELD_SEARCH_BOOK),
	):
		pack("search", parent_frame, side="left", expand=True, fill="both")
		parent_frame.pack_propagate(False)

		str_var = variable(var, tk.StringVar(parent_frame, value="INPUT"))
		str_var.trace_add("write", input_cb)

		pack("search", tk.Label(parent_frame, text=text), side="top", fill="x")
		pack("search", tk.Entry(parent_frame, textvariable=str_var), side="top", fill="x")

		tree = ttk.Treeview(parent_frame, columns=fieldnames, show="headings")
		for key in fieldnames:
			tree.heading(key, text=key.replace("_", " ").title())
		tree.bind("<<TreeviewSelect>>", tree_cb)

		sb = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=tree.yview)
		tree.configure(yscroll=sb.set)
		pack("search", sb, side="right", fill="y")

		ws["tree"].append(pack("search", tree, side="top", expand=True, fill="both"))

		# Set var to empty to execute the callback and fill the listtree
		str_var.set("")

	pack("search", tk.Button(parent_frame, text="Check me out!"))
	tree = get_search_tree_side(1)
	for col, width in enumerate((len(fmt_id(0)), 8, 4, 8, 8), start=1):
		tree.column(f"#{col}", width=CHAR_SIZE*(2+width))

	# --- Checkout Tab --- #

	# --- Recommend Tab --- #

	frame.pack(side="right", expand=True, fill="both")
	return frame

# --- Show Page --- #
def show_page(title: Literal['search', 'checkout', 'recommend']):
	for child in state["main"].pack_slaves():
		child.pack_forget()
	root.title(f"{TITLE} - {title.title()} {ICONS[title.split(maxsplit=1)[0].lower()]}")
	for w, p in state["pack"][title].items():
		w.pack(**p)

# --- Data Type Display Formats --- #
TAB = "    " # not using \t as it does not appear in tkinter
FWIDTH: int = 1
Colour: TypeAlias = str
COLOURS: dict[str, Colour] = {
	"in": "#00ff00", # In Stock
	"out": "#ffe600", # Out on Loan
	"over": "#ff0000", # Overdue
}
def colour_lookup(book: db.Book) -> Colour:
	try:
		log = checkout.find_log(book)
		if search.old([book]):
			return COLOURS["over"]
		return COLOURS["out"]
	except ValueError:
		return COLOURS["in"]

def fmt_id(id: int) -> str:
	return f"#{id:0{len(str(len(db.books())))}d}"
def fmt_title(title: str) -> str:
	return title.replace("\"", "").title()
def fmt_genre(genres: list[str]) -> str:
	return ", ".join(genres[:3]) + (", ..." if len(genres) > 3 else "")

def fmt_field(key: str, value: Any) -> str:
	return globals().get(f"fmt_{key}", str)(value)
def fmt(obj: dict[str, Any]) -> dict[str, str]:
	return {k: fmt_field(k,v) for k,v in obj.items()}

def fmt_group(group: db.Group) -> str:
	CWIDTH = FWIDTH // CHAR_SIZE - len(TAB) - 2
	size = max(0, CWIDTH - len(group['title']))
	p = f" {fmt_title(group['title'])}{TAB}{group['author']: >{size}}"
	return p
def fmt_book(book: db.Book) -> str:
	# try:
	# 	log = find_log(book)
	# 	if checked_out(book):
	# 		dates = ""
	# except ValueError:
	# 	dates = ""
	dates = ""
	return f" {fmt_id(book['id'])}{TAB}{book['purchase']}{TAB}{dates}"

def decompose_fmt_id(id: str) -> db.Book:
	return db.from_id(int(id[1:]))

# --- Search Page Functions & Callbacks --- #
def get_search_term(name: str) -> str:
	return state["var"][name].get().strip()
def get_search_tree_side(side: int) -> ttk.Treeview:
	return state["search"]["tree"][side]

def replace_tree_content(tree: ttk.Treeview, fields: Iterable[str], items: Iterable[dict[str, str] | tuple[dict[str, str], str]]):
	tree.delete(*tree.get_children())
	for item in items:
		if isinstance(item, dict):
			v = fmt(item)
			tree.insert("", tk.END, values=tuple(v.get(k, "") for k in fields))
		else: # tuple[row, colour]
			print(item)
			v = fmt(item[0])
			iid = tree.insert("", tk.END, values=tuple(v.get(k, "") for k in fields))
			# print(tree.item(iid))

def search_group_input_cb(a, b, c):
	term = get_search_term("group")
	tree = get_search_tree_side(0)
	replace_tree_content(tree, db.FIELD_VISUAL_GROUP, search.generate_group(term))

def search_group_list_cb(event):
	# Note here that Tkinter passes an event object to onselect()
	tree: ttk.Treeview = event.widget
	try:
		value: list[str] = list(map(str, tree.item(tree.selection()[0])["values"]))
	except IndexError:	return
	for group in search.active_groups:
		v = [fmt_field(k, group[k]) for k in db.FIELD_VISUAL_GROUP]
		if v == value:
			return active_group(group)

def search_book_input_cb(a, b, c):
	term = get_search_term("book")
	replace_tree_content(get_search_tree_side(1), FIELD_SEARCH_BOOK, ((i | checkout.get_log(i), colour_lookup(i)) for i in search.fuzzy_id(term) if {
		k: i[k] for k in db.FIELD_NAMES_GROUP # Convert to group of the book
	} == active_group()))

def search_book_list_cb(event):
	# Note here that Tkinter passes an event object to onselect()
	tree: ttk.Treeview = event.widget
	try:
		value: list[str] = tree.item(tree.selection()[0])["values"]
	except IndexError:	return
	return active_book(decompose_fmt_id(value[FIELD_SEARCH_BOOK.index("id")]))

def resize(wig):
	if wig is not root:
		return
	global FWIDTH
	FWIDTH = state["search"]["tree"][0].winfo_width()
	search_group_input_cb(None, None, None)

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
setup_screen(root)
show_page("search")
# root.state("zoomed")
root.update()
resize(root)
root.mainloop()
