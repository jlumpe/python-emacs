"""Python interface to GNU Emacs."""

__author__ = 'Jared Lumpe'
__email__ = 'mjlumpe@gmail.com'
__version__ = '0.2.0'


from .emacs import EmacsBatch, EmacsClient, ElispException
from .elisp import E
