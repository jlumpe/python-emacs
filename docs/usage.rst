.. py:currentmodule:: emacs.emacs


Basic usage
===========

Most of the functionality in this package is implemented in the :class:`Emacs`
class, which represents an interface into the Emacs program.


Instantiating the Emacs interface
---------------------------------

You should generally create the :class:`Emacs` object using one of the following
two class methods rather than invoking the constructor directly.

If you create the object with :meth:`Emacs.batch`, it will start a new Emacs
process with the ``--batch`` argument each time you run a command or evaluate
Elisp code. This will be slow if your ``init.el`` file takes a while to execute.

Alternatively, :meth:`Emacs.client` will create an instance which connects to
an already-running Emacs process using the ``emacsclient`` program. This should
make most commands run much faster. If you use this method make sure to start
the server in Emacs using ``(server-start)``.

If the ``verbose`` keyword argument is set to 1 or higher, the subprocess'
``stderr`` stream will be redirected to the console. If set to 2 ``stdout`` will
be displayed as well.


Low-level interface
-------------------

At the lowest level, you can call the :meth:`Emacs.run` or
:meth:`Emacs.getoutput` methods to invoke the program with the given list of
command line arguments. The difference between the two is that
:meth:`Emacs.getoutput` returns the value of stdout as a string while
:meth:`Emacs.run` returns an entire :class:`subprocess.CompletedProcess`
instance.


Executing Emacs lisp code
-------------------------

The main job of :class:`Emacs` is to execute elisp code.
You can do this using the :meth:`Emacs.eval` method::

    >>> emacs = Emacs.batch()
    >>> emacs.eval('(print "Hello world!")')
    '\n"Hello world!"\n'

This method records the output from stdout and returns it as a string.

Alternatively, you can use the :meth:`Emacs.getresult` method which returns the
result of the execution as a Python value::

    >>> emacs.getresult('(+ 1 2)')
    3

Note that it does this by converting the value to JSON in Emacs and then decoding
it in Python, so the value must be json-encodable.
