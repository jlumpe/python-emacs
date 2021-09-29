"""Interface with Emacs and run commands."""

import sys
from typing import Optional, Union, Sequence, List
import os
from subprocess import run, PIPE, CalledProcessError, CompletedProcess
import json
from contextlib import contextmanager
from tempfile import TemporaryDirectory
import logging

from .elisp import Expr, E, Raw


StrOrExpr = Union[str, Expr]
StrOrExprOrList = Union[StrOrExpr, Sequence[StrOrExpr]]


def _get_exprs_seq(seq: StrOrExpr) -> List[Expr]:
	exprs = []
	for item in seq:
		if isinstance(item, str):
			exprs.append(Raw(item))
		elif isinstance(item, Expr):
			exprs.append(item)
		else:
			raise TypeError('Sequence elements must be strings or Expr instances.')
	return exprs


def get_expr(src: StrOrExprOrList) -> Expr:
	"""Get source as list of forms from string, single form, or sequence of these."""
	if isinstance(src, Expr):
		return src

	if isinstance(src, str):
		return Raw(src)

	return E.progn(*_get_exprs_seq(src))


def get_exprs_list(src: StrOrExprOrList) -> List[Expr]:
	"""Get source as list of expression from string, AST node, or sequence of these."""
	if isinstance(src, Expr):
		return [src]

	if isinstance(src, str):
		return [Raw(src)]

	return _get_exprs_seq(src)


class EmacsException(Exception):
	"""An exception that occurred when trying to evaluate Elisp code in an emacs process.

	Attributes
	----------
	src
		Elisp code the process was trying to evaluate.
	stdout
		Process' stdout.
	stderr
		Process' stderr.
	"""
	src: StrOrExpr
	stdout: str
	stderr: str

	def __init__(self, src: StrOrExpr, stdout: str = None, stderr: str = None):
		self.src = src
		self.stdout = stdout
		self.stderr = stderr

	@classmethod
	def from_calledprocess(cls, src: StrOrExpr, cpe: CalledProcessError) -> 'EmacsException':
		"""Create from a CalledProcessError.

		Parameters
		----------
		src
			Source code which was to be evaluated.
		cpe
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
	cmd
		Base command to run Emacs.
	is_client
	    Whether the command runs ``emacsclient``.
	verbose
		1 to echo stderr of Emacs command, 2 to echo stdout. 0 turns off.

	Parameters
	----------
	cmd : list[str]
		Base command to run Emacs.
	client : bool
	    Whether the command runs ``emacsclient``.
	"""
	cmd: Union[str, List[str]]
	is_client: bool
	verbose: int
	logger: logging.Logger

	def __init__(self, cmd: Union[str, List[str]], client: bool = False, logger: Optional[logging.Logger] = None):
		if isinstance(cmd, str):
			self.cmd = [cmd]
		else:
			self.cmd = list(cmd)

		self.is_client = client
		self.logger = logger or logging.getLogger(__name__)

	@classmethod
	def batch(cls, args: Sequence[str] = (), **kwargs) -> 'Emacs':
		"""Create instance with default settings to run in batch mode.

		Parameters
		----------
		args
			Extra arguments to pass the ``emacs`` command.
		"""
		cmd = ['emacs', '--batch', *args]
		return cls(cmd, client=False, **kwargs)

	@classmethod
	def client(cls, args: Sequence[str] = (), **kwargs) -> 'Emacs':
		"""Create instance with default settings to run in client mode.

		Parameters
		----------
		args
			Extra arguments to pass the ``emacsclient`` command.
		"""
		cmd = ['emacsclient', *args]
		return cls(cmd, client=True, **kwargs)

	def run(self, args: Sequence[str], check: bool = True, verbose: Optional[int] = None) -> CompletedProcess:
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args
			List of strings.
		check
			Check the return code is zero.
		verbose
			Overrides :attr:`verbose` attribute if not None.

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

	def _getoutput(self, result: CompletedProcess) -> str:
		"""Get the output of a command."""
		return result.stdout.decode()

	def getoutput(self, args: Sequence[str], **kwargs) -> str:
		"""Get output of command.

		Parameters
		----------
		args
			List of strings.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		str
			Value of stdout.
		"""
		return self._getoutput(self.run(args, **kwargs))

	def eval(self, source: StrOrExprOrList, process: bool = False, **kwargs) -> Union[str, CompletedProcess]:
		"""Evaluate Elisp source code and return output.

		Parameters
		----------
		source
			Elisp code. If a list of strings/expressions will be enclosed in ``progn``.
		process
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
		source = str(get_expr(source))

		try:
			result = self.run(['--eval', source], **kwargs)
		except CalledProcessError as exc:
			raise EmacsException.from_calledprocess(source, exc)

		if process:
			return result
		else:
			return self._getoutput(result)

	def _result_from_stdout(self, expr: Expr, **kwargs) -> str:
		"""Get result by reading from stdout."""
		raise NotImplementedError()

	@contextmanager
	def _tmpfile(self) -> str:
		"""Make a temporary file to write/read emacs output to/from.

		Returns a context manager which gives the path to the temporary file on
		enter and removes the file on exit.
		"""
		with TemporaryDirectory() as tmpdir:
			yield os.path.join(tmpdir, 'emacs-output')

	def write_result(self, source: StrOrExprOrList, path: str):
		"""Have Emacs evaluate an elisp expression and write its result to a file.

		Parameters
		----------
		source
			Elisp code to evaluate.
		path
			File path to write to.
		"""
		el = E.with_temp_file(str(path), E.insert(source))
		self.eval(el)

	def _json_from_tmpfile(self, expr: StrOrExprOrList, encoding: str = 'utf8'):
		"""Write result of evaluating expression to temporary file and parse as JSON."""
		with self._tmpfile() as tmpfile:
			self.write_result(expr, tmpfile)
			with open(tmpfile, encoding=encoding) as f:
				return json.load(f)

	def getresult(self, source: StrOrExprOrList, is_json: str = False, **kwargs):
		"""Get parsed result from evaluating the Elisp code.

		Parameters
		----------
		source
			Elisp code to evaluate.
		is_json
			True if the result of evaluating the code is already a string of JSON-encoded data.

		Returns
		-------
		Any
			Parsed value.

		Raises
		------
		.EmacsException
			If an error occurred trying to execute the elsip code.
		"""
		expr = get_expr(source)

		if not is_json:
			expr = E.progn(
				E.require(E.Q('json')),
				E.json_encode(expr)
			)

		return self._json_from_tmpfile(expr, **kwargs)
