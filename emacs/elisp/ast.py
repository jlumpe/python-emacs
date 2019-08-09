"""Base classes for Emacs Lisp abstract syntax trees."""

import re
from functools import singledispatch


__all__ = ['ElispAstNode', 'Form', 'Literal', 'Symbol', 'Cons', 'List', 'Quote',
           'Raw', 'to_elisp', 'make_list', 'symbols', 'quote', 'cons']


class ElispAstNode:
	"""Abstract base class for Elisp AST nodes."""

	def __repr__(self):
		return '<el %s>' % self


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
			items.extend([Symbol(':' + key), to_elisp(value)])
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
		return '(%s . %s)' % (self.car, self.cdr)


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
		return "'%s" % self.form


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
def to_elisp(value):
	"""Convert a Python value to an Elisp AST node.

	Parameters
	----------
	value
		Python value to convert.

	Returns
	-------
	.ElispAstNode
	"""
	if isinstance(value, ElispAstNode):
		return value
	raise TypeError('Cannot convert object of type %s to Elisp' % type(value).__name__)


@to_elisp.register(bool)
@to_elisp.register(type(None))
def _bool_to_elisp(value):
	return Symbol('t') if value else Symbol('nil')


# Register literal types
for type_ in Literal.PY_TYPES:
	to_elisp.register(type_, Literal)


# Convert Python lists to quoted Emacs lists
@to_elisp.register(list)
def _py_list_to_el_list(pylist):
	return Quote(make_list(pylist))


@to_elisp.register(tuple)
def make_list(items):
	"""Make an Elisp list from a Python sequence, first converting its elements to Elisp.

	Parameters
	----------
	items : Iterable of objects to convert to list.

	Returns
	-------
	.List
	"""
	return List(map(to_elisp, items))


def quote(value):
	"""Quote value, converting Python strings to symbols.

	Parameters
	----------
	value : Elisp value to quote.

	Returns
	-------
	.Quote
	"""
	if isinstance(value, str):
		form = Symbol(value)
	else:
		form = to_elisp(value)

	return Quote(form)


def cons(car, cds):
	"""Create a Cons cell, converting arguments.

	Returns
	-------
	.Cons
	"""
	return Cons(to_elisp(car), to_elisp(cds))


def symbols(*names):
	"""Create a list of symbols.

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

	return List(s)



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


