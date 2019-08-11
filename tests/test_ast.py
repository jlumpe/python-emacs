"""Test Elisp AST node classes."""

import emacs.elisp as el


# Some reusable node constants
T = el.Symbol('t')
NIL = el.Symbol('nil')

SYMBOLS = [T, NIL] + list(map(el.Symbol, ['foo', ':foo', '+']))
LITERALS = list(map(el.Literal, [0, 1, -1, 0.0, 1.0, "foo", "bar", ""]))
CONS = [el.Cons(el.Literal(0), el.Literal(1)), el.Cons(el.Symbol('foo'), el.Literal('bar'))]
LISTS = list(map(el.List, [
	[],
	[el.Literal(i) for i in range(1, 4)],
	[el.Literal(s) for s in ['foo', 'bar', 'baz']],
]))
QUOTES = [el.Quote(n) for l in [SYMBOLS, LITERALS, CONS, LISTS] for n in l[:2]]
RAW = [el.Raw('(+ 1 2)'), el.Raw('(message "hello")')]

NODES = SYMBOLS + LITERALS + CONS + LISTS


def test_equality():
	"""Test equality of AST nodes."""

	for l in LITERALS:
		assert l == el.Literal(l.pyvalue)

	for s in SYMBOLS:
		assert s == el.Symbol(s.name)

	for c in CONS:
		assert c == el.Cons(c.car, c.cdr)

	for l in LISTS:
		assert l == el.List(l.items)

	for q in QUOTES:
		assert q == el.Quote(q.form)

	# Check inequality - these should all be pairwise unequal
	for i, item1 in enumerate(NODES):
		for item2 in NODES[i + 1:]:
			assert item1 != item2

			# Check quoted versions of pair as well
			assert el.Quote(item1) != el.Quote(item2)
			assert el.Quote(item1) != item1
			assert el.Quote(item1) != item2
			assert el.Quote(item2) != item1
			assert el.Quote(item2) != item2


def test_convert():
	"""Test conversion of Python values."""

	# Bools and none to t and nil
	assert el.to_elisp(None) == NIL
	assert el.to_elisp(False) == NIL
	assert el.to_elisp(True) == T

	# Wrap numbers and strings in literals
	assert el.to_elisp(1) == el.Literal(1)
	assert el.to_elisp(1.0) == el.Literal(1.0)
	assert el.to_elisp("foo") == el.Literal("foo")

	# Tuples to lists
	tup = ((3.14, "bar", NIL, (1, 2)))
	assert el.to_elisp(tup) == el.List(list(map(el.to_elisp, tup)))

	# Lists become quoted
	assert el.to_elisp(list(tup)) == el.Quote(el.to_elisp(tup))

	# Mapping objects converted as alists
	d = {'a': 1, 'b': 'foo', 'c': True}
	assert el.to_elisp(d) == el.make_alist(d)

	# Should leave existing nodes unchanged
	for n in NODES:
		assert el.to_elisp(n) == n


def test_symbol_call():
	"""Test that calling a symbol creates a function call."""
	assert el.Symbol('+')(1, 2) == el.List([el.Symbol('+'), 1, 2])


def test_str():
	"""Test conversion to str."""
	assert list(map(str, SYMBOLS)) == ['t', 'nil', 'foo', ':foo', '+']

	assert list(map(str, LITERALS)) == ['0', '1', '-1', '0.0', '1.0', '"foo"', '"bar"', '""']

	assert str(el.List([1, el.Symbol('a'), "b"])) == '(1 a "b")'

	assert str(el.Cons(el.Symbol('a'), 1)) == '(cons a 1)'

	assert str(el.Quote(el.Symbol('foo'))) == '\'foo'
	assert str(el.Quote(el.List([1, el.Symbol('a'), "b"]))) == '\'(1 a "b")'
	assert str(el.Quote(el.Cons(el.Symbol('a'), 1))) == '\'(a . 1)'

	assert str(el.Raw('(+ 1 2)')) == '(+ 1 2)'


def test_quote():
	"""Test quote() function."""
	sym = el.Symbol('a')
	assert el.quote(sym) == el.Quote(sym)
	assert el.quote('a') == el.Quote(sym)

	l = el.List([1, 2, 3])
	assert el.quote(l) == el.Quote(l)


def test_symbols():
	"""Test the symbols() function."""
	syms = el.symbols('a', 'b', 'c')
	assert syms == el.List(list(map(el.Symbol, 'abc')))
	assert el.symbols('a', 'b', 'c', quote=True) == el.Quote(syms)


def test_make_alist():
	"""Test the make_alist() function."""
	d = {'a': 1, 'b': ('foo', el.Symbol('bar')), 42: True}
	assert el.make_alist(d) == el.List([
		el.Cons(el.Symbol('a'), el.Literal(1)),
		el.Cons(el.Symbol('b'), el.to_elisp(d['b'])),
		el.Cons(el.Literal(42), el.Symbol('t')),
	])
	assert el.make_alist(d, quote=True) == el.Quote(el.make_alist(d))


def test_make_plist():
	"""Test the make_plist() function."""
	d = {'a': "foo", 'b': (1, 2, 3), 'c': True}
	assert el.make_plist(d) == el.List([
		el.Symbol('a'), el.Literal("foo"),
		el.Symbol('b'), el.to_elisp(d['b']),
		el.Symbol('c'), el.Symbol('t'),
	])
	assert el.make_plist(d, quote=True) == el.Quote(el.make_plist(d))
