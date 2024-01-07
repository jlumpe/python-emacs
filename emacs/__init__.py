"""Python interface to GNU Emacs."""

__version__ = '0.2.1'


from .emacs import EmacsBatch, EmacsClient, ElispException
from .elisp import E
