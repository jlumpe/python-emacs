import time
import subprocess as sp
from contextlib import contextmanager

import pytest

from emacs import EmacsBatch, EmacsClient


SERVER_NAME = 'pytest'
DAEMON_ARGS = ['-Q', f'--fg-daemon={SERVER_NAME}']


def make_batch():
	return EmacsBatch(args=['-Q'])

def make_client():
	return EmacsClient(server=SERVER_NAME)


@contextmanager
def daemon_context(startup=.25):
	proc = sp.Popen(['emacs', *DAEMON_ARGS], stdout=sp.PIPE, stderr=sp.PIPE)

	try:
		# Allow some time to start up
		time.sleep(startup)
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
def daemon():
	"""An emacs daemon process that is kept alive for the duration of the test(s)."""
	with daemon_context() as daemon:
		yield daemon


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
