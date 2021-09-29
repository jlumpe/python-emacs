"""A DSL for writing Elisp in Python.

God help us all.
"""

from .ast import *


class ElispDSL:
	"""Implements the ELisp DSL.
	"""

	def __getitem__(self, name) -> Symbol:
		"""Indexing with string gets a Symbol."""
		return Symbol(name)

	def _convert_symbol_name(self, name):
		"""Convert symbol name from Python style to Elisp style."""
		return name.replace('_', '-')

	def __getattr__(self, name):
		"""Attribute access with lower-case name gets a symbol."""
		if name[0] == name[0].lower() and not name.startswith('__'):
			return Symbol(self._convert_symbol_name(name))

		return object.__getattribute__(self, name)

	def __call__(self, value) -> Expr:
		"""Calling as function converts value."""
		return to_elisp(value)

	Q = staticmethod(quote)
	C = staticmethod(Cons)
	S = staticmethod(symbols)
	R = staticmethod(Raw)


#: Instance of :class:`ElispDSL` for easy importing.
E = ElispDSL()
