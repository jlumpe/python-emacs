.. py:currentmodule:: emacs.emacs


Basic usage
===========

Most of the functionality in this package is implemented in the :class:`EmacsBatch` and
:class:`EmacsClient` classes, which allow you to evaluate Emacs Lisp code and get the result in
Python. Both inherit from :class:`EmacsBase` and share the same API.


EmacsBatch
----------

:class:`EmacsBatch` runs ``emacs --batch`` with each invocation. The ``args`` constructor argument
is a list of additional command line arguments to add. It is often a good idea to use the ``-Q``
option to avoid loading personal configuration files each time, which can slow things down.

.. doctest::

   >>> from emacs import EmacsBatch
   >>> emacs = EmacsBatch(args=['-Q'])


EmacsClient
-----------

:class:`EmacsClient` uses the ``emacsclient`` command to connect to and execute code in a running
Emacs server. A server can be started in a running Emacs process by calling
``(server-start <server-name>)``. Alternatively you can start a daemon server with
``emacs --daemon=<server-name>``.

::

   >>> from emacs import EmacsClient
   >>> emacs = EmacsClient(server="my-server")   # doctest: +SKIP


Executing Emacs lisp code
-------------------------

The main job of the interface is to execute elisp code. You can do this using the :meth:`EmacsBase.eval`
method:

.. doctest::

   >>> emacs.eval('(+ 1 2)')
   3

The source code can be passed in as a string, or you can build an Elisp expression using the
:mod:`emacs.elisp` subpackage. This allows you to easily pass in data from Python:

.. doctest::

   >>> import emacs.elisp as el
   >>> def emacs_add(a, b):
   ...     expr = el.funccall('+', a, b)
   ...     return emacs.eval(expr)
   >>> emacs_add(1, 2)
   3

Note that it does this by converting the value to JSON in Emacs and then decoding
it in Python, so the value must be json-encodable.

Errors in evaluating the expression are caught in Emacs (see the ``catch_errors`` argument to
:func:`EmacsBase.eval`) and raised as an :exc:`~emacs.emacs.ElispException` in Python:

.. doctest::

   >>> emacs_add(1, "foo")
   Traceback (most recent call last):
   ElispException: Wrong type argument: number-or-marker-p, "foo"
