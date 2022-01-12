.. py:currentmodule:: emacs.elisp.ast


Representing Emacs lisp code in Python
======================================

The :mod:`emacs.elisp` module contains utilities for representing Emacs lisp
Abstract Syntax Trees (AST's) as Python objects, see the :class:`Expr`
abstract class and its subclasses.


Creating Elisp expressions
--------------------------

The fundamental data type in Elisp is the list. Other data types include symbols
and self-evaluating types such as strings or numbers.

Use the :func:`to_elisp` function to convert simple Python values to their Elisp
equivalents. This will wrap numbers and strings as Elisp literals, as well as
convert bools and None to the correct symbols:

.. doctest::

   >>> import emacs.elisp as el

   >>> el.to_elisp(123)
   <el 123>

   >>> el.to_elisp(1.23)
   <el 1.23>

   >>> el.to_elisp('foo')
   <el "foo">

   >>> el.to_elisp(True)
   <el t>

   >>> el.to_elisp(False)
   <el nil>

   >>> el.to_elisp(None)
   <el nil>


Python lists are converted to quoted Elisp lists, while tuples are left unquoted:

.. doctest::

   >>> el.to_elisp([1, 2, 3])
   <el '(1 2 3)>

   >>> el.to_elisp(('a', 'b', 'c'))
   <el ("a" "b" "c")>


Python dicts and other mapping types are converted using :func:`make_alist` (see
below):

.. doctest::

   >>> el.to_elisp({'a': 1, 'b': 2})
   <el ((cons a 1) (cons b 2))>


Elements of composite data types (lists, tuples, dicts) are recursively
converted using :meth:`to_elisp` if they are not already instances of
:class:`Expr`.

You can use :func:`quote` to quote a value. It will also convert strings to
quoted symbols:

.. doctest::

   >>> s = el.Symbol('foo')
   >>> s
   <el foo>

   >>> el.quote(s)
   <el 'foo>

   >>> el.quote('foo')
   <el 'foo>


An expression that must be constructed directly because it has no Python equivalent
is the cons cell, represented with the class :class:`Cons`:

.. doctest::

   >>> el.Cons(el.Symbol('a'), 1)
   <el (cons a 1)>

   >>> el.quote(el.Cons(el.Symbol('a'), 1))
   <el '(a . 1)>


The :func:`symbols` function can be used to create a list of symbols:

.. doctest::

   >>> el.symbols('a', 'b', 'c')
   <el (a b c)>

   >>> el.symbols('a', 'b', 'c', quote=True)
   <el '(a b c)>


You can use :func:`make_alist` or :func:`make_plist` to convert common mapping
types to their Elisp equivalents. These functions will always treat string
keys as symbols:

.. doctest::

   >>> el.make_alist({'a': 1, 'b': 2}, quote=True)
   <el '((a . 1) (b . 2))>

   >>> el.make_plist({':x': 1, ':y': 2}, quote=True)
   <el '(:x 1 :y 2)>


Finally, use :class:`Raw` to wrap a raw Elisp code string so that it will just
be inserted verbatim in the given location:

.. doctest::

   >>> el.Raw('(print "hi")')
   <el (print "hi")>


Using Elisp expressions
-----------------------

.. py:currentmodule:: emacs.emacs


Elisp expressions can be passed to :meth:`Emacs.eval` and :meth:`Emacs.getresult` for
execution. You can also convert them to strings to produce (hopefully)
syntactically-correct Elisp code.


Elisp DSL
---------

.. py:currentmodule:: emacs.elisp.ast


This package also includes an unholy abomination of a DSL that lets you write
Elisp code in Python. The DSL is implemented through a singleton object which
is importable as :data:`emacs.elisp.E <emacs.elisp.dsl.E>`::

   >>> from emacs.elisp import E


Calling the singleton as a function converts a Python object into an Elisp object
using :meth:`to_elisp`:

.. doctest::

   >>> E(3)
   <el 3>

   >>> E('foo')
   <el "foo">

   >>> E(['a', 'b', 'c'])
   <el '("a" "b" "c")>


Attribute access produces Elisp symbols, converting underscores to dashes. The
same can be done by indexing with a string:

.. doctest::

   >>> E.abc
   <el abc>

   >>> E.foo_bar
   <el foo-bar>

   >>> E[':baz']
   <el :baz>


Symbols can be called as functions, generating Elisp function calls:

.. doctest::

   >>> E.message("Hello from %s", E('python-emacs'))
   <el (message "Hello from %s" "python-emacs")>


Additionally, the ``Q``, ``C``, ``S``, and ``R`` methods are aliases for the
:func:`quote`, :class:`Cons`, :func:`symbols`, and :class:`Raw`, respectively.

Using just the ``E`` object, it is possible to write complex Elisp expressions:

.. doctest::

   >>> E.defun(E.my_elisp_function, E.S('a', 'b'),
   ...   E.message("I shouldn't exist"),
   ...   E['+'](E.a, E.b))
   <el (defun my-elisp-function (a b) (message "I shouldn't exist") (+ a b))>
