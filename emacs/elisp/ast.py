"""Base classes for Emacs Lisp abstract syntax trees."""

from typing import Any, Union, Tuple, Iterable, List as PyList
import re
from functools import singledispatch
from collections.abc import Mapping


__all__ = ['Expr', 'Literal', 'Symbol', 'Cons', 'List', 'Quote',
           'Raw', 'to_elisp', 'make_alist', 'make_plist', 'symbols', 'quote']


class Expr:
	"""Base for classes which represent Elisp expressions."""

	def __str__(self):
		"""Render the expression as elisp code."""
		raise NotImplementedError()

	def __repr__(self):
		return '<el %s>' % self

	def _quoted(self) -> str:
		"""Get representation within a quoted expression."""
		return str(self)


class Literal(Expr):
	"""Basic self-evaluating expressions like strings, numbers, etc.

	Attributes
	----------
	pyvalue
		The Python value of the literal.
	"""
	PY_TYPES = (str, int, float)

	pyvalue: Any

	def __init__(self, pyvalue: Union[PY_TYPES]):
		if not isinstance(pyvalue, self.PY_TYPES):
			raise TypeError('Instances of %s not allowed as Elisp literals' % type(pyvalue))
		self.pyvalue = pyvalue

	def __eq__(self, other):
		return isinstance(other, Literal) \
		       and type(other.pyvalue) is type(self.pyvalue) \
		       and other.pyvalue == self.pyvalue

	def __str__(self):
		if isinstance(self.pyvalue, str):
			return print_elisp_string(self.pyvalue)
		else:
			return str(self.pyvalue)


class Symbol(Expr):
	"""An Elisp symbol."""

	name: str

	def __init__(self, name: str):
		assert isinstance(name, str) and name
		self.name = name

	def __eq__(self, other):
		return isinstance(other, Symbol) and other.name == self.name

	@property
	def isconst(self) -> bool:
		return self.name.startswith(':') or self.name in ('nil', 't')

	def __call__(self, *args, **kwargs) -> 'List':
		"""Produce a function call expression from this symbol."""
		items = [self, *map(to_elisp, args)]
		for key, value in kwargs.items():
			s = Symbol(':' + key.replace('_', '-'))
			items.extend([s, to_elisp(value)])
		return List(items)

	def __str__(self):
		return self.name


class Cons(Expr):
	"""A cons cell."""

	car: Expr
	cdr: Expr

	def __init__(self, car, cdr):
		self.car = to_elisp(car)
		self.cdr = to_elisp(cdr)

	def __eq__(self, other):
		return isinstance(other, Cons) \
		       and other.car == self.car \
		       and other.cdr == self.cdr

	def __str__(self):
		return '(cons %s %s)' % (self.car, self.cdr)

	def _quoted(self) -> str:
		return '(%s . %s)' % (self.car._quoted(), self.cdr._quoted())


class List(Expr):
	"""A list...

	Attributes
	----------
	items
		Items in the list
	"""

	items: Tuple[Expr, ...]

	def __init__(self, items: Iterable):
		self.items = tuple(map(to_elisp, items))

	def __eq__(self, other):
		return isinstance(other, List) and other.items == self.items

	def __str__(self):
		return '(%s)' % ' '.join(map(str, self.items))

	def _quoted(self) -> str:
		return '(%s)' % ' '.join(item._quoted() for item in self.items)


class Quote(Expr):
	"""A quoted Elisp expression.

	Attributes
	----------
	expr
		The quoted Elisp expression.
	"""

	def __init__(self, expr: Expr):
		self.expr = to_elisp(expr)

	def __eq__(self, other):
		return isinstance(other, Quote) and other.expr == self.expr

	def __str__(self):
		return "'%s" % self.expr._quoted()


class Raw(Expr):
	"""Just raw Elisp code to be pasted in at this point.

	Attributes
	----------
	src
		Raw Elisp source code.
	"""

	src: str

	def __init__(self, src: str):
		self.src = src

	def __eq__(self, other):
		return isinstance(other, Raw) and other.src == self.src

	def __str__(self):
		return self.src


@singledispatch
def to_elisp(value, **kw) -> Expr:
	"""Convert a Python value to an Elisp expression.

	Parameters
	----------
	value
		Python value to convert.
	dict_format : str
		Elisp format to convert dicts/mappings to. Either ``'alist'`` (default) or ``'plist'``.

	Returns
	-------
	.Expr
	"""
	if isinstance(value, Expr):
		return value
	raise TypeError('Cannot convert object of type %s to Elisp' % type(value).__name__)


@to_elisp.register(bool)
@to_elisp.register(type(None))
def _bool_to_elisp(value, **kw):
	return Symbol('t') if value else Symbol('nil')



def _literal_to_elisp(value, **kw):
	return Literal(value)

# Register literal types
for type_ in Literal.PY_TYPES:
	to_elisp.register(type_, _literal_to_elisp)


@to_elisp.register(tuple)
def _make_el_list(iterable, **kw):
	return List([to_elisp(item, **kw) for item in iterable])


# Convert Python lists to quoted Emacs lists
@to_elisp.register(list)
def _py_list_to_el_list(pylist, **kw):
	return Quote(_make_el_list(pylist, **kw))


def quote(value: Union[str, Expr], **kw) -> Quote:
	"""Quote value, converting Python strings to symbols.

	Parameters
	----------
	value
		Elisp value or symbol name to quote.
	kw
		Keyword arguments passed to :func:`.to_elisp` if value needs to be converted.
	"""
	if isinstance(value, str):
		expr = Symbol(value)
	else:
		expr = to_elisp(value, **kw)

	return Quote(expr)


def symbols(*names: str, quote: bool = False) -> List:
	"""Create a list of symbols.

	Parameters
	----------
	names
		Symbol names.
	quote
		Whether quote the resulting list.
	"""

	s = []

	for name in names:
		if isinstance(name, str):
			s.append(Symbol(name))
		elif isinstance(name, Symbol):
			s.append(name)
		else:
			raise TypeError('Expected str or Symbol, got %s' % type(name).__name__)

	l = List(s)
	return Quote(l) if quote else l


def _convert_pairs(pairs, kw) -> PyList[Tuple[Expr, Expr]]:
	if isinstance(pairs, dict):
		pairs = pairs.items()

	l = []

	for key, value in pairs:
		key = Symbol(key) if isinstance(key, str) else to_elisp(key)
		l.append((key, to_elisp(value, **kw)))

	return l

def make_alist(pairs: Union[Mapping, Iterable[Tuple]], quote: bool = False, **kw) -> Expr:
	"""Create an alist from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	quote
		Quote the resulting expression.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.
	"""
	alist = List([Cons(key, value) for key, value in _convert_pairs(pairs, kw)])
	return Quote(alist) if quote else alist


def make_plist(pairs: Union[Mapping, Tuple[Any, Any]], quote: bool = False, **kw) -> Expr:
	"""Create a plist from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	quote
		Quote the resulting expression.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.
	"""
	plist = List([x for kv in _convert_pairs(pairs, kw) for x in kv])
	return Quote(plist) if quote else plist


@to_elisp.register(Mapping)
def _mapping_to_elisp(value, **kw):
	fmt = kw.get('dict_format', 'alist')
	if fmt == 'alist':
		return make_alist(value, **kw)
	if fmt == 'plist':
		return make_plist(value, **kw)
	raise ValueError('Invalid value for dict_format argument: %r' % fmt)


def print_elisp_string(string: str) -> str:
	"""Print string to Elisp, properly escaping it (maybe)."""
	return '"%s"' % re.sub(r'([\\\"])', r'\\\1', string)
