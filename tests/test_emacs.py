"""Test interaction with Emacs process."""

import subprocess as sp
import pytest




pytestmark = [pytest.mark.requires_emacs]


def test_daemon(daemon):
	"""Check the daemon fixture."""
	args = ['emacsclient', '-s', 'pytest', '--eval', 'server-name']
	result = sp.run(args, stdout=sp.PIPE, stderr=sp.PIPE)
	result.check_returncode()
	assert result.stdout.decode().strip() == f'"pytest"'


class TestInterface:

	def test_run(self, emacs):
		"""Test the run() method."""

		if emacs.is_client:
			pytest.xfail('Client output not working')

		args = ['--eval', '(princ "foo")']
		result = emacs.run(args)
		assert isinstance(result, sp.CompletedProcess)
		assert result.stdout.decode().strip() == 'foo'
		assert result.returncode == 0

		# Fail with syntax error
		args2 = ['--eval', '(']
		with pytest.raises(sp.CalledProcessError):
			emacs.run(args2)

		result2 = emacs.run(args2, check=False)
		assert result2.returncode != 0

	def test_eval(self, emacs):
		"""Test the eval() method."""

		if emacs.is_client:
			pytest.xfail('Client output not working')

		assert emacs.eval('(princ "foo")') == 'foo'

		cp = emacs.eval('(princ "foo")', process=True)
		assert isinstance(cp, sp.CompletedProcess)
		assert cp.stdout.decode() == 'foo'

		# Syntax error
		with pytest.raises(sp.CalledProcessError):
			emacs.eval('(')
