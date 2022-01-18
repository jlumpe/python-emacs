import emacs.elisp as el
from emacs.elisp import E


def test_getattr():
	assert E.foo == el.Symbol('foo')
	assert E.foo_bar == el.Symbol('foo-bar')
	assert E.__call__ == object.__getattribute__(E, '__call__')
	assert E.C is el.cons


def test_getitem():
	assert E['foo'] == el.Symbol('foo')
	assert E['foo_bar'] == el.Symbol('foo_bar')


def test_call():
	pass  # TODO
