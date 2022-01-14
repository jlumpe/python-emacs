import time
import subprocess as sp

import pytest

from emacs import Emacs


SERVER_NAME = 'pytest'
DAEMON_ARGS = ['-Q', f'--fg-daemon={SERVER_NAME}']


def make_batch():
	return Emacs.batch(['-Q'])

def make_client():
	return Emacs.client(['-s', SERVER_NAME])


@pytest.fixture(scope='module')
def daemon():
	"""An emacs daemon process that is kept alive for the duration of the test(s)."""
	proc = sp.Popen(['emacs', *DAEMON_ARGS], stdout=sp.PIPE, stderr=sp.PIPE)

	# Allow some time to start up
	time.sleep(1)

	try:
		assert proc.poll() is None, 'Daemon failed to start'

		yield proc

		# Should still be running
		assert proc.poll() is None, 'Daemon exited prematurely'

	finally:
		# Quit
		proc.terminate()
		proc.wait()

		# Log daemon output - by default only shown on test failure
		stdout = proc.stdout.read().decode()
		print('Emacs daemon stdout:')
		print(stdout.strip())

		stderr = proc.stderr.read().decode()
		print('Emacs daemon stderr:')
		print(stderr.strip())


@pytest.fixture()
def batch():
	return make_batch()


@pytest.fixture()
def client(daemon):
	return make_client()


@pytest.fixture(params=['client', 'batch'])
def emacs(request, daemon):
	"""Parameterized both EmacsBatch and EmacsClient."""
	if request.param == 'client':
		return make_client()
	elif request.param == 'batch':
		return make_batch()
	else:
		assert 0
