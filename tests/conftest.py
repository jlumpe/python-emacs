import time
import subprocess as sp

import pytest

from emacs import Emacs


SERVER_NAME = 'pytest'
DAEMON_ARGS = ['-Q', '--fg-daemon=' + SERVER_NAME]


def make_batch():
	return Emacs.batch(['-Q'])

def make_client():
	return Emacs.client(['-s', SERVER_NAME])


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
