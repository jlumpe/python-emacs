Manipulating Elisp code in Python
=================================

The :mod:`emacs.elisp` module contains utilities for building and manipulating Emacs Lisp (Elisp)
expressions in Python. These can then be passed to an :class:`~emacs.emacs.EmacsBatch` or
:class:`~emacs.emacs.EmacsClient` instance to be executed.


Expr Objects
------------

.. py:currentmodule:: emacs.elisp.ast

Elisp expressions are represented by subtypes of the :class:`Expr` abstract base class:

* :class:`Literal`\ ``(value)`` wraps Python ``int``\ s, ``str``\ s, and ``float``\ s.
* :class:`Symbol`\ ``(name: str)`` represents a symbol.
* :class:`Cons`\ ``(car: Expr, cdr: Expr)`` represents a cons cell.
* :class:`List`\ ``(items: Iterable[Expr])`` represents a list.
* :class:`Quote`\ ``(expr: Expr)`` represents a quoted expression.
* :class:`Raw`\ ``(src: str)`` can be used to wrap a raw Elisp code string.

Generally you should use the functions detailed in the following section to build expressions
rather than instantiating them directly.

You can use ``str(expr)`` to produce (hopefully) syntactically-correct Elisp code.


Building Elisp expressions
--------------------------

.. py:currentmodule:: emacs.elisp.exprs

The :func:`to_elisp` function can be used to convert various Python values to Elisp expressions.
Elements of composite data types (lists, tuples, dicts) are converted recursively.
Most parts of this package's API will use :func:`to_elisp` to convert arguments that are not already
instances of :class:`~emacs.elisp.ast.Expr`, so it is often not necessary to use it directly.


Basic data types
................

:func:`to_elisp` converts numbers and strings to literals and ``bool``\ s and ``None`` to the
correct symbols:

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

The ``nill`` and ``t`` symbols are also available as :data:`nil` and :data:`el_true`.


Symbols
.......

Create a symbol with the :func:`symbol` function:

.. doctest::

   >>> el.symbol('foo')
   <el foo>

The :func:`symbols` function can be used to create a list of symbols:

.. doctest::

   >>> el.symbols('a', 'b', 'c')
   <el (a b c)>


Lists
.....

:func:`el_list` converts any iterable to a list expression:

.. doctest::

   >>> el.el_list(range(1, 5))
   <el (1 2 3 4)>


:func:`to_elisp` converts Python lists to quoted Elisp lists, while tuples are left unquoted:

.. doctest::

   >>> el.to_elisp([1, 2, 3])
   <el '(1 2 3)>

   >>> el.to_elisp(('a', 'b', 'c'))
   <el ("a" "b" "c")>


Function calls
..............

Function call expressions can be created with :func:`funccall`, or by calling a
:class:`~emacs.elisp.ast.Symbol` instance. Keyword arguments are converted to
``kebab-case`` and prefixed with a ":" character.

.. doctest::

   >>> el.funccall('+', 1, 2)
   <el (+ 1 2)>

   >>> foo = el.symbol('foo')
   >>> foo(el.symbol('x'), el.symbol('y'), kw_arg=123)
   <el (foo x y :kw-arg 123)>


Quoting
.......

The :meth:`~emacs.elisp.ast.Expr.quote` method produces a quoted version of an
expression:

.. doctest::

   >>> s = el.symbol('foo')
   >>> s.quote()
   <el 'foo>

   >>> el.symbols('a', 'b', 'c').quote()
   <el '(a b c)>

The :attr:`~emacs.elisp.ast.Expr.q` property acts as a shortcut:

.. doctest::

   >>> s.q
   <el 'foo>


Cons cells
..........

An expression that must be constructed directly because it has no Python equivalent
is the cons cell, represented with the class :class:`~emacs.elisp.ast.Cons`:

.. doctest::

   >>> c = el.cons(el.symbol('a'), 1)
   >>> c
   <el (cons a 1)>

   >>> c.q
   <el '(a . 1)>


Mapping formats (alists and plists)
...................................

You can use :func:`make_alist` or :func:`make_plist` to convert mapping types like ``dict``\ s
to their Elisp equivalents. These functions will always treat string keys as symbols:

.. doctest::

   >>> el.make_alist({'a': 1, 'b': 2}).q
   <el '((a . 1) (b . 2))>

   >>> el.make_plist({':x': 1, ':y': 2}).q
   <el '(:x 1 :y 2)>


:func:`to_elisp` converts mapping types like dicts to plists or alists, depending on
the value of the ``dict_format`` argument (defaults to ``"alist"``.


Raw code strings
................

Finally, use :class:`~emacs.elisp.ast.Raw` to wrap a raw Elisp code string to be inserted verbatim
in the given location:

.. doctest::

   >>> el.Raw('(print "hi")')
   <el (print "hi")>

   >>> el.el_list([1, 2, el.Raw('(+ a b)')])
   <el (1 2 (+ a b))>


Elisp DSL
---------

This package also includes an unholy abomination of a DSL that lets you write Elisp code in Python.
It is implemented through the singleton object :data:`emacs.elisp.E <emacs.elisp.dsl.E>`.

Calling the singleton as a function converts a Python object into an Elisp object
using :meth:`to_elisp`:

.. doctest::

   >>> from emacs.elisp import E
   >>> E(3)
   <el 3>

   >>> E('foo')
   <el "foo">

   >>> E(['a', 'b', 'c'])
   <el '("a" "b" "c")>


Attribute access produces Elisp symbols, converting ``snake_case`` to ``kebab-case``. The
same can be done by indexing with a string (without the case conversion):

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

   >>> E['='](E.a, E.b)
   <el (= a b)>


Additionally, the ``C``, ``S``, and ``R`` methods are aliases for
:class:`cons`, :func:`symbols`, and :class:`~emacs.elisp.ast.Raw`, respectively.

Using just the ``E`` object, it is possible to write complex Elisp expressions:

.. doctest::

   >>> E.defun(E.my_elisp_function, E.S('a', 'b'),
   ...   E.message("I am a crime against God."),
   ...   E['+'](E.a, E.b))
   <el (defun my-elisp-function (a b) (message "I am a crime against God.") (+ a b))>
