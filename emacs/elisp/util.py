"""Other utility code relating to Elisp."""

from io import StringIO
from typing import Union
from ast import literal_eval


def snake_to_kebab(name: str) -> str:
	"""Convert a symbol name from ``'snake_case'`` to ``'kebab-case'``."""
	return name.replace('_', '-')


def escape_emacs_char(c: Union[int, str]) -> str:
	"""Escape character for use in Elisp string literal."""
	i = c if isinstance(c, int) else ord(c)

	# Backslash
	if i == 0x5c:
		return r'\\'

	# Double quote
	if i == 0x22:
		return r'\"'

	# Printable
	if 0x20 <= i <= 0x7F:
		return chr(i)

	# Two-digit hex
	if i <= 0xFF:
		return f'\\x{i:02X}'

	# Four-digit hex
	if i <= 0xFFFF:
		return f'\\u{i:04X}'

	# Eight-digit hex
	if i <= 0xFFFFFFFF:
		return f'\\U{i:08X}'

	raise ValueError(i)


def escape_emacs_string(s: str, quotes: bool=False) -> str:
	"""Escape non-printable characters in a way that can be read by Emacs.

	If ``quotes=True`` this returns a valid Elisp string literal that evaluates to ``s`` and can be
	read by the ``read`` function.

	Parameters
	----------
	s
		String to escape.
	quotes
		Surround output with double quote characters.
	"""

	buf = StringIO()

	if quotes:
		buf.write('"')

	for c in s:
		buf.write(escape_emacs_char(c))

	if quotes:
		buf.write('"')

	return buf.getvalue()


def unescape_emacs_string(s: str, quotes: bool = False) -> str:
	"""Unescape the representation of a string printed by Emacs.

	This can be used to parse string printed using ``prin1``, for example.

	Important: this requires the Emacs variables ``print-escape-newlines`` and
	``print-escape-control-characters`` be set to ``t`` for certain control and whitespace
	characters to be escaped properly. See `here`__ for more information.

	__ https://www.gnu.org/software/emacs/manual/html_node/elisp/Output-Variables.html

	Parameters
	----------
	s
		String to escape.
	quotes
		Expect contents of ``s`` to be surrounded by double quote characters.
	"""
	if quotes:
		if (len(s) < 2 or not (s[0] == s[-1] == '"')):
			raise ValueError('String must begin and end with double quotes.')
	else:
		s = '"' + s + '"'

	try:
		return literal_eval(s)
	except SyntaxError as e:
		raise ValueError(f'Invalid Emacs string literal {s!r}') from e
