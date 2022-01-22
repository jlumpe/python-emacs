"""Test interaction with Emacs process."""

import subprocess as sp

import pytest

from emacs import ElispException
import emacs.elisp as el
from emacs.elisp import E


pytestmark = [pytest.mark.requires_emacs]


def test_daemon(daemon):
	"""Check the daemon fixture."""
	args = ['emacsclient', '-s', 'pytest', '--eval', 'server-name']
	result = sp.run(args, stdout=sp.PIPE, stderr=sp.PIPE)
	result.check_returncode()
	assert result.stdout.decode().strip() == f'"pytest"'


class TestInterface:
	"""Test the common interface of the EmacsBatch and EmacsClient classes."""

	def _write_to_file(self, path, s):
		"""Expression to write a string to a file."""
		return E.with_temp_file(str(path), E.insert(str(s)))

	def test_run(self, emacs, tmp_path):
		"""Test the run() method."""

		f = tmp_path / 'test'
		s = 'foo'

		args = ['--eval', str(self._write_to_file(f, s))]
		result = emacs.run(args)

		assert isinstance(result, sp.CompletedProcess)
		assert result.returncode == 0

		with open(f) as fh:
			assert fh.read() == s

	def test_run_err(self, emacs):
		"""Test process exiting abnormally with run()."""

		args = ['--eval', '(']
		with pytest.raises(sp.CalledProcessError):
			emacs.run(args)

		result = emacs.run(args, check=False)
		assert result.returncode != 0

	@pytest.mark.parametrize('catch_errors', [True, False])
	@pytest.mark.parametrize('use_tmpfile', [True, False])
	def test_eval_value(self, emacs, catch_errors, use_tmpfile):
		"""Test getting value of an elisp expression with the eval() method."""

		items = [
			('(+ 1 2)', 3),
			('(/ 1.0 2)', .5),
			('(concat "foo" "bar")', 'foobar'),
			('(> 2 1)', True),
			('(> 1 2)', None),
			('nil', None),
			(el.el_list([1, 1.5, "foo", el.nil]).q, [1, 1.5, "foo", None]),
		]

		for expr, expected in items:
			val = emacs.eval(expr, catch_errors=catch_errors, tmpfile=use_tmpfile)
			assert val == expected

	def test_eval_nonzero_exit(self, emacs):
		"""Test error when Emacs returns with a nonzero exit code."""

		with pytest.raises(sp.CalledProcessError):
			emacs.eval('(')

	@pytest.mark.parametrize('catch_errors', [True, False])
	@pytest.mark.parametrize('use_tmpfile', [True, False])
	def test_eval_elisp_error(self, emacs, catch_errors, use_tmpfile):
		"""Test error in Emacs when evaluating."""

		expr = 'foo'
		errcls = ElispException if catch_errors else sp.CalledProcessError

		with pytest.raises(errcls) as exc_info:
			emacs.eval(expr, catch_errors=catch_errors, tmpfile=use_tmpfile)

		if catch_errors:
			e = exc_info.value
			assert e.message == 'Symbol’s value as variable is void: foo'
			assert e.symbol == 'void-variable'
			assert e.data == ['foo']
			assert isinstance(e.expr, el.Expr)
			assert isinstance(e.proc, sp.CompletedProcess)

	@pytest.mark.parametrize('ret', ['value', 'process', 'both', 'none', None])
	@pytest.mark.parametrize('catch_errors', [True, False])
	@pytest.mark.parametrize('use_tmpfile', [True, False])
	def test_eval_ret(self, emacs, ret, catch_errors, use_tmpfile):
		"""Test eval() method ret argument."""

		val = "foo"

		retval = emacs.eval(el.Literal(val), ret=ret, catch_errors=catch_errors, tmpfile=use_tmpfile)

		if ret == 'value':
			assert retval == val
		elif ret == 'process':
			assert isinstance(retval, sp.CompletedProcess)
			assert retval.returncode == 0
		elif ret == 'both':
			v, cp = retval
			assert v == val
			assert isinstance(cp, sp.CompletedProcess)
			assert cp.returncode == 0
		elif ret in ('none', None):
			assert retval is None
		else:
			assert 0


class TestEmacsBatch:
	"""Tests specific to EmacsBatch class."""


class TestEmacsClient:
	"""Tests specific to EmacsClient class."""

	def test_persistence(self, client):
		"""Test variable definitions persist in daemon through multiple calls."""
		client.eval(E.setq(E.x, "foo"))
		client.eval(E.setq(E.y, "bar"))
		assert client.eval(E.concat(E.x, E.y)) == "foobar"
