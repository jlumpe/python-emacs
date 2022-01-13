"""Other utility code relating to Elisp."""

import re


def snake_to_kebab(name: str) -> str:
      """Convert a symbol name from ``'snake_case'`` to ``'kebab-case'``."""
      return name.replace('_', '-')


def print_elisp_string(string: str) -> str:
      """Print string to Elisp, properly escaping it (maybe)."""
      return '"%s"' % re.sub(r'([\\\"])', r'\\\1', string)
