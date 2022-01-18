"""Test emacs.elisp.ast"""

import pytest

import emacs.elisp as el


# Some reusable expression constants
SYMBOLS = list(map(el.Symbol, ['nil', 'foo', ':foo', '+']))
LITERALS = list(map(el.Literal, [0, 1, -1, 0.0, 1.0, "foo", "bar", ""]))
CONS = [el.cons(el.Literal(0), el.Literal(1)), el.cons(el.Symbol('foo'), el.Literal('bar'))]
LISTS = list(map(el.List, [
	[],
	[el.Literal(i) for i in range(1, 4)],
	[el.Literal(s) for s in ['foo', 'bar', 'baz']],
]))
QUOTES = [el.Quote(n) for l in [SYMBOLS, LITERALS, CONS, LISTS] for n in l[:2]]
RAW = [el.Raw('(+ 1 2)'), el.Raw('(message "hello")')]

EXPRS = SYMBOLS + LITERALS + CONS + LISTS + RAW


def check_pw_equality(items):
	"""Check items are equal to themselves but not each other."""

	for i, item1 in enumerate(items):
		for j, item2 in enumerate(items):
			if i == j:
				assert item1 == item2
			else:
				assert item1 != item2


class TestLiteral:

	def test_eq(self):
		check_pw_equality(LITERALS)

		for l in LITERALS:
			assert l == el.Literal(l.pyvalue)

	def test_str(self):
		assert list(map(str, LITERALS)) == ['0', '1', '-1', '0.0', '1.0', '"foo"', '"bar"', '""']


class TestSymbol:

	def test_eq(self):
		check_pw_equality(SYMBOLS)

		for s in SYMBOLS:
			assert s == el.Symbol(s.name)

	def test_str(self):
		assert list(map(str, SYMBOLS)) == ['nil', 'foo', ':foo', '+']

	def test_call(self):
		"""Test that calling a symbol creates a function call."""
		assert el.Symbol('+')(1, 2) == el.el_list([el.Symbol('+'), 1, 2])


class TestCons:

	def test_eq(self):
		check_pw_equality(CONS)

		for c in CONS:
			assert c == el.Cons(c.car, c.cdr)

	def test_str(self):
		c = el.cons(el.Symbol('a'), 1)
		assert str(c) == '(cons a 1)'
		assert str(c.q) == '\'(a . 1)'


class TestList:

	def test_eq(self):
		check_pw_equality(LISTS)

		for l in LISTS:
			assert l == el.List(l.items)

	def test_str(self):
		assert str(el.el_list([1, el.Symbol('a'), "b"])) == '(1 a "b")'


class TestQuote:

	def test_eq(self):
		check_pw_equality(QUOTES)

		for q in QUOTES:
			assert q == el.Quote(q.expr)
			assert q != q.expr

	def test_str(self):
		assert str(el.Quote(el.Symbol('foo'))) == '\'foo'
		assert str(el.Quote(el.el_list([1, el.Symbol('a'), "b"]))) == '\'(1 a "b")'


class TestRaw:

	def test_eq(self):
		check_pw_equality(RAW)

	def test_str(self):
		assert str(el.Raw('(+ 1 2)')) == '(+ 1 2)'
