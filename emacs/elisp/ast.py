"""Base classes for Emacs Lisp abstract syntax trees."""

import re
from functools import singledispatch
from collections.abc import Mapping


__all__ = ['ElispAstNode', 'Form', 'Literal', 'Symbol', 'Cons', 'List', 'Quote',
           'Raw', 'to_elisp', 'make_alist', 'make_plist', 'symbols', 'quote']


class ElispAstNode:
	"""Abstract base class for Elisp AST nodes."""

	def __repr__(self):
		return '<el %s>' % self

	def _quoted(self):
		"""Get representation within a quote form."""
		return str(self)


class Form(ElispAstNode):
	"""Pretty much everything is a form, right?"""


class Literal(Form):
	"""Basic self-evaluating forms like strings, numbers, etc.

	Attributes
	----------
	pyvalue
		The Python value of the literal.
	"""

	PY_TYPES = (str, int, float)

	def __init__(self, pyvalue):
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


class Symbol(Form):
	"""Elisp symbol.

	Attributes
	----------
	name : str
	"""

	def __init__(self, name):
		assert isinstance(name, str) and name
		self.name = name

	def __eq__(self, other):
		return isinstance(other, Symbol) and other.name == self.name

	@property
	def isconst(self):
		return self.name.startswith(':') or self.name in ('nil', 't')

	def __call__(self, *args, **kwargs):
		"""Produce a function call node from this symbol."""
		items = [self, *map(to_elisp, args)]
		for key, value in kwargs.items():
			s = Symbol(':' + key.replace('_', '-'))
			items.extend([s, to_elisp(value)])
		return List(items)

	def __str__(self):
		return self.name


class Cons(Form):
	"""A cons cell.

	Attributes
	----------
	car : .ElispAstNode
	cdr : .ElispAstNode
	"""

	def __init__(self, car, cdr):
		self.car = to_elisp(car)
		self.cdr = to_elisp(cdr)

	def __eq__(self, other):
		return isinstance(other, Cons) \
		       and other.car == self.car \
		       and other.cdr == self.cdr

	def __str__(self):
		return '(cons %s %s)' % (self.car, self.cdr)

	def _quoted(self):
		return '(%s . %s)' % (self.car._quoted(), self.cdr._quoted())


class List(Form):
	"""A list...

	Attributes
	----------
	items : tuple of .ElispAstNode
		Items in the list
	"""

	def __init__(self, items):
		self.items = tuple(map(to_elisp, items))

	def __eq__(self, other):
		return isinstance(other, List) and other.items == self.items

	def __str__(self):
		return '(%s)' % ' '.join(map(str, self.items))

	def _quoted(self):
		return '(%s)' % ' '.join(item._quoted() for item in self.items)


class Quote(Form):
	"""A quoted Elisp form.

	Attributes
	----------
	form : .ElispAstNode
		The quoted Elisp form.
	"""

	def __init__(self, form):
		self.form = to_elisp(form)

	def __eq__(self, other):
		return isinstance(other, Quote) and other.form == self.form

	def __str__(self):
		return "'%s" % self.form._quoted()


class Raw(ElispAstNode):
	"""Just raw Elisp code to be pasted in at this point.

	Attributes
	----------
	src : str
		Raw Elisp source code.
	"""

	def __init__(self, src):
		self.src = src

	def __eq__(self, other):
		return isinstance(other, Raw) and other.src == self.src

	def __str__(self):
		return self.src


@singledispatch
def to_elisp(value, **kw):
	"""Convert a Python value to an Elisp AST node.

	Parameters
	----------
	value
		Python value to convert.
	dict_format : str
		Elisp format to convert dicts/mappings to. Either ``'alist'`` (default)
		or ``'plist'``.

	Returns
	-------
	.ElispAstNode
	"""
	if isinstance(value, ElispAstNode):
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


def quote(value, **kw):
	"""Quote value, converting Python strings to symbols.

	Parameters
	----------
	value
		Elisp value to quote.
	kw
		Keyword arguments passed to :func:`.to_elisp` if value needs to be
		converted.

	Returns
	-------
	.Quote
	"""
	if isinstance(value, str):
		form = Symbol(value)
	else:
		form = to_elisp(value, **kw)

	return Quote(form)


def symbols(*names, quote=False):
	"""Create a list of symbols.

	Parameters
	----------
	names
		Symbol names.
	quote : bool
		Quote the resulting list.

	Returns
	-------
	.List
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


def _convert_pairs(pairs, kw):
	if isinstance(pairs, dict):
		pairs = pairs.items()

	l = []

	for key, value in pairs:
		key = Symbol(key) if isinstance(key, str) else to_elisp(key)
		l.append((key, to_elisp(value, **kw)))

	return l


def make_alist(pairs, quote=False, **kw):
	"""Create an alist from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	quote : bool
		Quote the resulting form.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.

	Returns
	-------
	ElispAstNode
	"""
	alist = List([Cons(key, value) for key, value in _convert_pairs(pairs, kw)])
	return Quote(alist) if quote else alist


def make_plist(pairs, quote=False, **kw):
	"""Create a plist from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	quote : bool
		Quote the resulting form.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.

	Returns
	-------
	ElispAstNode
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


def print_elisp_string(string):
	"""Print string to Elisp, properly escaping it (maybe).

	Parameters
	----------
	string : str

	Returns
	-------
	str
	"""
	return '"%s"' % re.sub(r'([\\\"])', r'\\\1', string)
