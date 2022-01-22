# python-emacs
[![CI](https://github.com/jlumpe/python-emacs/actions/workflows/ci.yml/badge.svg)](https://github.com/jlumpe/python-emacs/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/python-emacs/badge/?version=latest)](https://python-emacs.readthedocs.io/en/latest/?badge=latest)


This package provides an interface between Python and GNU Emacs. It allows you to easily pass data
from Python to Emacs, execute Emacs Lisp code, and transfer the resulting data back to Python again.
It also provides utilities for building Emacs Lisp expressions in Python.


## Installation

Install using pip:

    pip install python-emacs

Or directly from the repository:

    git clone https://github.com/jlumpe/python-emacs
    cd python-emacs
    pip install .


## Usage

Create an interface to Emacs using either `EmacsBatch` or `EmacsClient`. The first runs a new Emacs
process in batch mode with every command, the second uses `emacsclient` to communicate with a
running server. Both follow the same API.

```python-console
>>> from emacs import EmacsBatch
>>> emacs = EmacsBatch(args=['-Q'])  # Don't load user config with each invocation
```

Execute an Elisp expression and get the result:

```python-console
>>> emacs.eval('(+ 1 2)')
3

>>> emacs.eval('(format "One plus two is %d" (+ 1 2))')
'One plus two is 3'

>>> src = '''
... (progn
...   (require 'cl)
...   (cl-loop
...     for i in '(1 2 3 4 5)
...     collect (* i i)))
... '''

>>> emacs.eval(src)
[1, 4, 9, 16, 25]
```

Evaluation errors are caught in Emacs and raised in Python:

```python-console
>>> emacs.eval('(+ 1 "foo")')
ElispException: Wrong type argument: number-or-marker-p, "foo"
```


## Write Elisp programs in Python

```python-console
>>> import emacs.elisp as el

>>> src = el.to_elisp((el.Symbol('format'), 'One plus two is %d', (el.Symbol('+'), 1, 2)))
>>> src
<el (format "One plus two is %d" (+ 1 2))>

>>> emacs.eval(src)
'One plus two is 3'
```

Using a terrible DSL:

```python-console
>>> from emacs.elisp import E

>>> prog = E.with_output_to_string(
      E.dolist(
        (E.i, E.number_sequence(1, 20)),
        E.princ(E.i),
        E.when(E['='](E['%'](E.i, 3), 0), E.princ("fizz")),
        E.when(E['='](E['%'](E.i, 5), 0), E.princ("buzz")),
        E.princ('\n')))

>>> prog
<el (with-output-to-string (dolist (i (number-sequence 1 20)) (princ i) (when (= (% i 3) 0) (princ "fizz")) (when (= (% i 5) 0) (princ "buzz")) (princ "\n")))>

>>> print(emacs.eval(prog))
1
2
3fizz
4
5buzz
6fizz
7
8
9fizz
10buzz
11
12fizz
13
14
15fizzbuzz
16
17
18fizz
19
20buzz
```
