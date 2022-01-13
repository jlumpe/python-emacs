"""Test interaction with Emacs process."""

import subprocess as sp
import time

import pytest

from emacs.emacs import Emacs


pytestmark = [pytest.mark.requires_emacs]


DAEMON_NAME = 'pytest'
DAEMON_ARGS = ['-Q', '--fg-daemon=' + DAEMON_NAME]


@pytest.fixture(scope='module')
def daemon():
	"""An emacs daemon process that is kept alive for the duration of the test(s)."""
	proc = sp.Popen(['emacs', *DAEMON_ARGS])

	# Allow some time to start up
	time.sleep(1)

	assert proc.poll() is None
	try:
		yield proc

	finally:
		# Should still be running
		assert proc.poll() is None
		# Quit
		proc.terminate()
		proc.wait()


def test_daemon(daemon):
	"""Check the daemon fixture."""
	args = ['emacsclient', '-s', DAEMON_NAME, '--eval', 'server-name']
	result = sp.run(args, stdout=sp.PIPE, stderr=sp.PIPE)
	result.check_returncode()
	assert result.stdout.decode().strip() == f'"{DAEMON_NAME}"'


class TestInterface:
	"""Test the Emacs class."""

	@pytest.fixture(params=['client', 'batch'])
	def emacs(self, request, daemon):
		if request.param == 'client':
			return Emacs.client(['-s', DAEMON_NAME])
		elif request.param == 'batch':
			return Emacs.batch(['-Q'])
		else:
			assert 0

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
