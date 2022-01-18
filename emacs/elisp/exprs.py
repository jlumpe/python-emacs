"""Functions to build Elisp expressions (more) easily."""

from typing import Any, Union, Tuple, Iterable, List as PyList, Sequence
from collections.abc import Mapping
from functools import singledispatch

from .ast import Expr, Literal, Symbol, Cons, List, Quote, Raw
from .util import snake_to_kebab


_StrOrExpr = Union[str, Expr]
StrOrExprOrList = Union[_StrOrExpr, Sequence[_StrOrExpr]]


#: The ``nil`` symbol
nil = Symbol('nil')

#: The standard Elisp representation of True
el_true = Symbol('t')


def el_bool(value: bool) -> Expr:
	"""Convert a Python boolean to the standard Elisp representation."""
	return el_true if value else nil


def el_list(items: Iterable, *, convert_kw=None) -> List:
	"""Create an Elisp list expression, converting items to Elisp expressions if needed.

	Parameters
	----------
	items
		Contents of list.
	convert_kw
		Keyword arguments to :func:`.to_elisp`.
	"""
	if convert_kw is None:
		convert_kw = dict()

	return List([to_elisp(item, **convert_kw) for item in items])


@singledispatch
def to_elisp(value, **kw) -> Expr:
	"""Convert a Python value to an Elisp expression.

	The following conversions are supported:

	* ``True`` to ``t`` symbol.
	* ``False`` and ``None`` to ``nil`` symbol.
	* ``int``, ``float``, and ``str`` to literals.
	* ``tuple`` to unquoted elisp list.
	* ``list`` to quoted elisp list.
	* ``dict`` and other mapping types to either alist or plist, see the ``dict_format`` argument.
	* :class:`.Expr` instances are returned unchanged.

	For compound types, their contents are recursively converted as well.

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
	raise TypeError('Cannot convert object of type %s to Elisp' % type(value).__name__)


to_elisp.register(Expr, lambda v, **kw: v)
to_elisp.register(type(None), lambda v, **kw: nil)
to_elisp.register(bool, lambda v, **kw: el_bool(v))
to_elisp.register(tuple, lambda v, **kw: el_list(v, convert_kw=kw))
to_elisp.register(list, lambda v, **kw: Quote(el_list(v, convert_kw=kw)))

for type_ in Literal.PY_TYPES:
	to_elisp.register(type_, lambda v, **kw: Literal(v))


@to_elisp.register(Mapping)
def _mapping_to_elisp(value, **kw):
	fmt = kw.get('dict_format', 'alist')
	if fmt == 'alist':
		return make_alist(value, convert_kw=kw)
	if fmt == 'plist':
		return make_plist(value, convert_kw=kw)
	raise ValueError('Invalid value for dict_format argument: %r' % fmt)


def symbol(name: Union[str, Symbol], kebab: bool = False, keyword: bool = False) -> Symbol:
	"""Convert argument to symbol.

	Parameters
	----------
	name
		Symbol name as string. Alternatively, an existing symbol instance which will be returned
		unchanged.
	kebab
		Convert name from ``snake_case`` to ``kebab-case``.
	keyword
		Prefix name with ":" character if it doesn't start with it already.
	"""
	if isinstance(name, Symbol):
		return name

	if not isinstance(name, str):
		raise TypeError('Expected str or Symbol, got %s' % type(name).__name__)

	if kebab:
		name = snake_to_kebab(name)
	if keyword and not name.startswith(':'):
		name = ':' + name

	return Symbol(name)


def symbols(*names: Union[str, Symbol]) -> Expr:
	"""Create an Elisp list of symbols.

	Parameters
	----------
	names
		Symbol names.
	"""
	return List([symbol(name) for name in names])


def cons(car, cdr, *, convert_kw=None) -> Cons:
	"""Create a cons cell expression, converting both arguments first.

	Parameters
	----------
	car
	cdr
	convert_kw
		Keyword arguments to :func:`.to_elisp`.
	"""
	if convert_kw is None:
		convert_kw = dict()
	return Cons(to_elisp(car, **convert_kw), to_elisp(cdr, **convert_kw))


def funccall(f: Union[str, Symbol], *args, **kw):
	"""Create a function call expression.

	Parameters
	----------
	f
		Function name or symbol
	args
		Function arguments. Will be converted to Elisp expressions if necessary.
	kw
		Keyword arguments. Argument names are converted like ``my_num=1`` -> ``:my-num 1``.
	"""
	items = [symbol(f), *map(to_elisp, args)]

	for key, value in kw.items():
		s = symbol(key, kebab=True, keyword=True)
		items.extend([s, to_elisp(value)])

	return List(items)


def _convert_pairs(pairs, kw) -> PyList[Tuple[Expr, Expr]]:
	if isinstance(pairs, dict):
		pairs = pairs.items()

	l = []

	for key, value in pairs:
		key = Symbol(key) if isinstance(key, str) else to_elisp(key)
		l.append((key, to_elisp(value, **kw)))

	return l


def make_alist(pairs: Union[Mapping, Iterable[Tuple]], **kw) -> Expr:
	"""Create an alist expression from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	quote
		Quote the resulting expression.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.
	"""
	return List([Cons(key, value) for key, value in _convert_pairs(pairs, kw)])


def make_plist(pairs: Union[Mapping, Tuple[Any, Any]], **kw) -> Expr:
	"""Create a plist expression from a set of key-value pairs.

	Parameters
	----------
	pairs
		Key-value pairs as a dict or collections of 2-tuples.
	kw
		Keyword arguments passed to :func:`to_elisp` to convert mapping values.
	"""
	return List([x for kv in _convert_pairs(pairs, kw) for x in kv])


def get_src(src: StrOrExprOrList) -> Expr:
	"""Get Elisp source code as :class:`.Expr` instance.

	Parameters
	----------
	src
		Elisp expression(s) as either a string containing raw Elisp code, a single ``Expr``, or a list
		of these.

	Returns
	-------
	.Expr
		Source code as single expression. If the input was a list it will be enclosed in a
		``progn`` block.
	"""
	if isinstance(src, Expr):
		return src

	if isinstance(src, str):
		return Raw(src)

	# Enclose in (progn ...)
	exprs = []
	for x in src:
		if isinstance(x, str):
			exprs.append(Raw(x))
		elif isinstance(x, Expr):
			exprs.append(x)
		else:
			raise TypeError(f'Statements must be instances of str or Expr, got {type(x).__name__}')

	return Symbol('progn')(*exprs)


def let(assignments, *body) -> List:
	"""Make a "let" expression.

	Parameters
	----------
	assignments
		Mapping from variable names (as symbols or strings) to values.
	body
		Expressions to add to body.
	"""
	varlist = List([
		List([symbol(snake_to_kebab(k)), to_elisp(v)])
		for k, v in assignments.items()
	])
	return funccall('let', varlist, *body)
