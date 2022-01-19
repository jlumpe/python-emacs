"""Base classes for Emacs Lisp abstract syntax trees."""

from typing import Union, Tuple, Iterable

from .util import escape_emacs_string


class Expr:
	"""Base for classes which represent Elisp expressions."""

	def __str__(self):
		"""Render the expression as elisp code."""
		raise NotImplementedError()

	def quote(self) -> 'Expr':
		"""Return a quoted form of this expression."""
		return Quote(self)

	@property
	def q(self):
		"""Shortcut for ``self.quote()``."""
		return self.quote()

	def __repr__(self):
		return '<el %s>' % self

	def _repr_quoted(self) -> str:
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

	pyvalue: Union[PY_TYPES]

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
			return escape_emacs_string(self.pyvalue, quotes=True)
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
		"""Produce a function call expression from this symbol.

		See :func:`emacs.elisp.ast.funccall`.
		"""
		from .exprs import funccall
		return funccall(self, *args, **kwargs)

	def __str__(self):
		return self.name


class Cons(Expr):
	"""A cons cell."""

	car: Expr
	cdr: Expr

	def __init__(self, car: Expr, cdr: Expr):
		self.car = car
		self.cdr = cdr

	def __eq__(self, other):
		return isinstance(other, Cons) \
		       and other.car == self.car \
		       and other.cdr == self.cdr

	def __str__(self):
		return '(cons %s %s)' % (self.car, self.cdr)

	def _repr_quoted(self) -> str:
		return '(%s . %s)' % (self.car._repr_quoted(), self.cdr._repr_quoted())


class List(Expr):
	"""An Elisp list expression.

	Attributes
	----------
	items
		Items in the list.
	"""

	items: Tuple[Expr, ...]

	def __init__(self, items: Iterable[Expr]):
		self.items = tuple(items)

	def __eq__(self, other):
		return isinstance(other, List) and other.items == self.items

	def __str__(self):
		return '(%s)' % ' '.join(map(str, self.items))

	def _repr_quoted(self) -> str:
		return '(%s)' % ' '.join(item._repr_quoted() for item in self.items)


class Quote(Expr):
	"""A quoted Elisp expression.

	Attributes
	----------
	expr
		The quoted Elisp expression.
	"""

	def __init__(self, expr: Expr):
		self.expr = expr

	def __eq__(self, other):
		return isinstance(other, Quote) and other.expr == self.expr

	def __str__(self):
		return "'" + self.expr._repr_quoted()


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
