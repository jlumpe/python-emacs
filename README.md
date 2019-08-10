# python-emacs
[![Build Status](https://travis-ci.org/jlumpe/python-emacs.svg?branch=master)](https://travis-ci.org/jlumpe/python-emacs)

Python interface to GNU Emacs.


## Installation

Install using pip:

    pip install python-emacs
    
Or directly from the repository:

    git clone https://github.com/jlumpe/python-emacs
    cd python-emacs
    python setup.py install
    
    
## Usage

Create an interface to Emacs using either `Emacs.batch()` or `Emacs.client()`. The first runs a new Emacs process in batch mode with every command, the second uses `emacsclient` to communicate with an already-running process.

```python-console
>>> from emacs import Emacs
>>> emacs = Emacs.batch(['-q'])
```

Execute some Elisp code and get the output:

```python-console
>>> src = '(princ (format "One plus two is %d" (+ 1 2)))'
>>> emacs.eval(src)
'One plus two is 3'
```

Get the result of an expression as a Python value:

```python-console
>>> emacs.getresult('(format "One plus two is %d" (+ 1 2))')
'One plus two is 3'

>>> emacs.getresult('(cl-loop for i in \'(1 2 3 4 5) collect (* i i))')
[1, 4, 9, 16, 25]
```


## Write Elisp programs in Python

```python-console
>>> import emacs.elisp as el

>>> src = el.to_elisp((el.Symbol('format'), 'One plus two is %d', (el.Symbol('+'), 1, 2)))
>>> src
<el (format "One plus two is %d" (+ 1 2))>

>>> emacs.getresult(src)
'One plus two is 3'
```

Using a terrible DSL:

```python-console
>>> from emacs.elisp import E

>>> prog = E.dolist((E.i, E.number_sequence(1, 20)),
      E.princ(E.i),
      E.when(E['='](E['%'](E.i, 3), 0), E.princ("fizz")),
      E.when(E['='](E['%'](E.i, 5), 0), E.princ("buzz")),
      E.princ('\n'),
    )
>>> prog
<el (dolist (i (number-sequence 1 20)) (princ i) (when (= (% i 3) 0) (princ "fizz")) (when (= (% i 5) 0) (princ "buzz")) (princ "\n"))>

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
