"""A DSL for writing Elisp in Python.

God help us all.
"""

from .ast import Expr, Symbol, Raw
from .exprs import to_elisp, symbols, cons
from .util import snake_to_kebab


class ElispDSL:
	"""Implements the Elisp DSL.
	"""

	def __getitem__(self, name) -> Symbol:
		"""Indexing with string gets a Symbol."""
		return Symbol(name)

	def __getattr__(self, name):
		"""Attribute access with lower-case name gets a symbol."""
		if name[0] == name[0].lower() and not name.startswith('__'):
			return Symbol(snake_to_kebab(name))

		return object.__getattribute__(self, name)

	def __call__(self, value) -> Expr:
		"""Calling as function converts value."""
		return to_elisp(value)

	C = staticmethod(cons)
	S = staticmethod(symbols)
	R = staticmethod(Raw)


#: Instance of :class:`ElispDSL` for easy importing.
E = ElispDSL()
