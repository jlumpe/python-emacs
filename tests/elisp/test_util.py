"""Test emacs.elisp.util."""

import string

import pytest
from pytest import param

import emacs.elisp as el
from emacs.elisp import util


ASCII = range(0x80)
ASCII_PRINTABLE = list(map(ord, string.printable))
ASCII_CONTROL = sorted(set(ASCII).difference(ASCII_PRINTABLE))


def cp2str(cp):
	"""Sequence of Unicode code points to string."""
	return ''.join(map(chr, cp))


def _string_params():
	return pytest.mark.parametrize(['s', 'output_broken'], [

		param('',                              False, id='Empty'),
		param(cp2str(ASCII_PRINTABLE),         False, id='ASCII printable'),
		param(cp2str(ASCII_CONTROL),           False, id='ASCII control'),
		param(cp2str(range(0x080, 0x100)),     True,  id='2-digit hex'),
		param(cp2str(range(0x100, 0x110)),     False, id='outside 2-digit hex'),
		param(cp2str(range(0o1000, 0o1010)),   False, id='outside 3-digit octal'),
		param(cp2str(range(0x10000, 0x10010)), False, id='outside 4-digit hex'),
		param(cp2str([0x10FFFF]),              False, id='max code point'),
	])

class TestStringEscaping:
	"""Test escaping/unescaping Elisp strings."""

	@_string_params()
	def test_roundtrip(self, s, output_broken):
		escaped = util.escape_emacs_string(s)
		unescaped = util.unescape_emacs_string(escaped)
		assert unescaped == s

		escaped2 = util.escape_emacs_string(s, quotes=True)
		assert escaped2 == '"' + escaped + '"'
		unescaped2 = util.unescape_emacs_string(escaped2, quotes=True)
		assert unescaped2 == s

	@pytest.mark.requires_emacs
	@_string_params()
	def test_escape_emacs(self, s, output_broken, batch):
		"""Test reading escaped string in emacs."""

		escaped = util.escape_emacs_string(s, quotes=True)
		src = f'(princ {escaped})'
		result = batch.run(['--eval', src])

		if output_broken:
			pytest.xfail('Emacs UTF-8 output incorrect for this character range')

		assert result.stdout == s.encode('utf-8')

	@pytest.mark.requires_emacs
	@_string_params()
	def test_unescape_emacs(self, s, output_broken, batch, tmp_path):
		"""Test unescaping string printed by emacs."""

		# Write raw string file
		file = tmp_path / 'string.txt'
		with open(file, 'w') as f:
			f.write(s)

		# Read from file and print string representation to stdout
		settings = dict(
			print_escape_newlines=True,
			print_escape_control_characters=True,
		)
		src = f'''
		(with-temp-buffer
		  (insert-file-contents "{file!s}")
		  (prin1 (buffer-string)))
		'''
		src = str(el.let(settings, el.Raw(src)))
		result = batch.run(['--eval', src])
		out = result.stdout.decode('utf-8')

		assert util.unescape_emacs_string(out, quotes=True) == s

	def test_unescape_invalid(self):
		"""Test unescaping invalid strings."""

		# Lacking quotes
		for s in ['foo', '"foo', '']:
			with pytest.raises(ValueError):
				util.unescape_emacs_string(s, quotes=True)

		# Invalid escaping
		for s in ['foo"bar']:
			with pytest.raises(ValueError):
				util.unescape_emacs_string(s, quotes=False)
