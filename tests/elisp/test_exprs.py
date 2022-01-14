"""Test emacs.elisp.exprs"""

import pytest

import emacs.elisp as el


def test_to_elisp():
	# Bools and none to t and nil
	assert el.to_elisp(None) == el.nil
	assert el.to_elisp(False) == el.nil
	assert el.to_elisp(True) == el.el_true

	# Wrap numbers and strings in literals
	assert el.to_elisp(1) == el.Literal(1)
	assert el.to_elisp(1.0) == el.Literal(1.0)
	assert el.to_elisp("foo") == el.Literal("foo")

	# Python tuples to lists
	tup = ((3.14, "bar", el.nil, (1, 2)))
	assert el.to_elisp(tup) == el.el_list(tup)

	# Python lists become quoted
	assert el.to_elisp(list(tup)) == el.Quote(el.el_list(tup))

	# Mapping objects converted as alists (default) or plists
	d = {'a': 1, 'b': 'foo', 'c': True}
	assert el.to_elisp(d) == el.make_alist(d)
	assert el.to_elisp(d, dict_format='plist') == el.make_plist(d)

	# Should leave existing exprs unchanged
	for expr in [el.symbol('foo'), el.Literal(1), el.List([])]:
		assert el.to_elisp(expr) is expr


def test_quote():
	sym = el.Symbol('a')
	assert el.quote(sym) == el.Quote(sym)
	assert el.quote('a') == el.Quote(sym)

	l = el.el_list([1, 2, 3])
	assert el.quote(l) == el.Quote(l)


def test_symbol():
	sym = el.Symbol('a')
	assert el.symbol(sym) == sym
	assert el.symbol(sym.name) == sym

	with pytest.raises(TypeError):
		el.symbol(0)


def test_symbols():
	syms = el.symbols('a', 'b', 'c')
	assert syms == el.List(list(map(el.Symbol, 'abc')))
	assert el.symbols('a', 'b', 'c', quote=True) == el.Quote(syms)


def test_funccall():
	f = el.symbol('+')
	args = [el.symbol('x'), 1]

	expr = el.funccall(f, *args)
	assert expr == el.el_list([f, *args])

	assert el.funccall(f.name, *args) == expr

	f2 = el.symbol('foo')
	kw = dict(kwarg=1, another_kwarg=[1, "kdj", 3])

	expr2 = el.funccall(f2, *args, **kw)
	assert expr2 == el.el_list([
		f2,
		*map(el.to_elisp, args),
		el.symbol(':kwarg'),
		el.to_elisp(kw['kwarg']),
		el.symbol(':another-kwarg'),
		el.to_elisp(kw['another_kwarg']),
	])


def test_make_alist():
	d = {'a': 1, 'b': ('foo', el.Symbol('bar')), 42: True}
	assert el.make_alist(d) == el.List([
		el.Cons(el.Symbol('a'), el.Literal(1)),
		el.Cons(el.Symbol('b'), el.to_elisp(d['b'])),
		el.Cons(el.Literal(42), el.el_true),
	])
	assert el.make_alist(d, quote=True) == el.Quote(el.make_alist(d))


def test_make_plist():
	"""Test the make_plist() function."""
	d = {'a': "foo", 'b': (1, 2, 3), 'c': True}
	assert el.make_plist(d) == el.List([
		el.Symbol('a'), el.Literal("foo"),
		el.Symbol('b'), el.to_elisp(d['b']),
		el.Symbol('c'), el.el_true,
	])
	assert el.make_plist(d, quote=True) == el.Quote(el.make_plist(d))


def test_let():
	assignments = dict(x=1, foo_bar=2)
	body = [
		el.funccall('setq', el.symbol('foo-bar'), 3),
		el.funccall('+', el.symbol('x'), el.symbol('foo-bar'))
	]
	expr = el.let(assignments, *body)

	assert isinstance(expr, el.List)
	assert expr.items[0] == el.symbol('let')
	assert expr.items[1] == el.List([
		el.List([el.Symbol('x'), el.Literal(1)]),
		el.List([el.Symbol('foo-bar'), el.Literal(2)]),
	])
	assert list(expr.items[2:]) == body
