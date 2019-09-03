"""Interface with Emacs and run commands."""

import sys
import os
from subprocess import run, PIPE, CalledProcessError
import json
from contextlib import contextmanager
from tempfile import TemporaryDirectory
import logging

from .elisp import ElispAstNode, E, Raw


def _get_forms_seq(seq):
	forms = []
	for item in seq:
		if isinstance(item, str):
			forms.append(Raw(item))
		elif isinstance(item, ElispAstNode):
			forms.append(item)
		else:
			raise TypeError('Sequence elements must be strings or AST nodes')
	return forms


def get_form(src):
	"""Get Elisp form from string, AST node, or sequence of these."""
	if isinstance(src, ElispAstNode):
		return src

	if isinstance(src, str):
		return Raw(src)

	return E.progn(*_get_forms_seq(src))


def get_forms_list(src):
	"""Get source as list of forms from string, AST node, or sequence of these."""
	if isinstance(src, ElispAstNode):
		return [src]

	if isinstance(src, str):
		return [Raw(src)]

	return _get_forms_seq(src)


class EmacsException(Exception):
	"""An exception that occurred when trying to evaluate Elisp code in an emacs process.

	Attributes
	----------
	src
		Elisp code the process was trying to evaluate.
	stdout : str
		Process' stdout.
	stderr : str
		Process' stderr.
	"""
	def __init__(self, src, stdout=None, stderr=None):
		self.src = src
		self.stdout = stdout
		self.stderr = stderr

	@classmethod
	def from_calledprocess(cls, src, cpe):
		"""Create from a CalledProcessError.

		Parameters
		----------
		src : str or emacs.elisp.ast.ElispAstNode
			Source code which was to be evaluated.
		cpe : subprocess.CalledProcessError

		Returns
		-------
		.EmacsException
		"""
		exc = cls(src, stdout=cpe.stdout, stderr=cpe.stderr)
		exc.__cause__ = cpe
		return exc


class Emacs:
	"""Interface to the GNU Emacs program.

	You shouldn't construct this class directly, instead use the :meth:`batch`
	or :meth:`client` class methods.

	Attributes
	----------
	cmd : str or list[str]
		Base command to run Emacs.
	is_client : bool
	    Whether the command runs ``emacsclient``.
	verbose : int
		1 to echo stderr of Emacs command, 2 to echo stdout. 0 turns off.

	Parameters
	----------
	cmd : list[str]
		Base command to run Emacs.
	client : bool
	    Whether the command runs ``emacsclient``.
	"""

	def __init__(self, cmd, client=False, logger=None):
		if isinstance(cmd, str):
			self.cmd = [cmd]
		else:
			self.cmd = list(cmd)

		self.is_client = client
		self.logger = logger or logging.getLogger(__name__)

	@classmethod
	def batch(cls, args=(), **kwargs):
		"""Create instance with default settings to run in batch mode.

		Parameters
		----------
		args : tuple
			Extra arguments to pass the ``emacs`` command.

		Returns
		-------
		.Emacs
		"""
		cmd = ['emacs', '--batch', *args]
		return cls(cmd, client=False, **kwargs)

	@classmethod
	def client(cls, args=(), **kwargs):
		"""Create instance with default settings to run in client mode.

		Parameters
		----------
		args : tuple
			Extra arguments to pass the ``emacsclient`` command.

		Returns
		-------
		.Emacs
		"""
		cmd = ['emacsclient', *args]
		return cls(cmd, client=True, **kwargs)

	def run(self, args, check=True, verbose=None):
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args : list[str]
			List of strings.
		check : bool
			Check the return code is zero.
		verbose : int or None
			Overrides :attr:`verbose` attribute if not None.

		Returns
		-------
		subprocess.CompletedProcess

		Raises
		------
		subprocess.CalledProcessError
			If ``check=True`` and return code is nonzero.
		"""
		cmd = [*self.cmd, *args]

		self.logger.info(cmd)
		result = run(cmd, check=False, stdout=PIPE, stderr=PIPE)

		if result.stderr:
			self.logger.warning(result.stderr.decode())
		if result.stdout:
			self.logger.debug(result.stdout.decode())

		if check:
			result.check_returncode()

		return result

	def _getoutput(self, result):
		"""Get the output of a command.

		Parameters
		----------
		result : subprocess.CompletedProcess

		Returns
		-------
		str
		"""
		return result.stdout.decode()

	def getoutput(self, args, **kwargs):
		"""Get output of command.

		Parameters
		----------
		args : list[str]
			List of strings.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		str
			Value of stdout.
		"""
		return self._getoutput(self.run(args, **kwargs))

	def eval(self, source, process=False, **kwargs):
		"""Evaluate ELisp source code and return output.

		Parameters
		----------
		source : str or list
			Elisp code. If a list of strings will be enclosed in ``progn``.
		process : bool
			If True return the :class:`subprocess.CompletedProcess` object,
			otherwise just return the value of ``stdout``.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		str or subprocess.CompletedProcess
			Command output or completed process object, depending on value of
			``process``.

		Raises
		------
		.EmacsException
			If an error occurred trying to execute the elsip code.
		"""
		source = str(get_form(source))

		try:
			result = self.run(['--eval', source], **kwargs)
		except CalledProcessError as exc:
			raise EmacsException.from_calledprocess(source, exc)

		if process:
			return result
		else:
			return self._getoutput(result)

	def _result_from_stdout(self, form, **kwargs):
		"""Get result by reading from stdout."""
		raise NotImplementedError()

	@contextmanager
	def _tmpfile(self):
		"""Make a temporary file to write/read emacs output to/from.

		Returns a context manager which gives the path to the temporary file on
		enter and removes the file on exit.
		"""
		with TemporaryDirectory() as tmpdir:
			yield os.path.join(tmpdir, 'emacs-output')

	def write_result(self, source, path):
		"""Have Emacs evaluate an elisp form and write its result to a file.

		Parameters
		----------
		source : str or list
			Elisp code to evaluate.
		path : str
			File path to write to.
		"""
		el = E.with_temp_file(str(path), E.insert(source))
		self.eval(el)

	def _json_from_tmpfile(self, form, encoding='utf8'):
		"""Write result of evaluating form to temporary file and parse as JSON."""
		with self._tmpfile() as tmpfile:
			self.write_result(form, tmpfile)
			with open(tmpfile, encoding=encoding) as f:
				return json.load(f)

	def getresult(self, source, is_json=False, **kwargs):
		"""Get parsed result from evaluating the Elisp code.

		Parameters
		----------
		source : str or list
			Elisp code to evaluate.
		is_json : bool
			True if the result of evaluating the code is already a string of
			JSON-encoded data.

		Returns
		-------
		object
			Parsed value.

		Raises
		------
		.EmacsException
			If an error occurred trying to execute the elsip code.
		"""
		form = get_form(source)

		if not is_json:
			form = E.progn(
				E.require(E.Q('json')),
				E.json_encode(form)
			)

		return self._json_from_tmpfile(form, **kwargs)
