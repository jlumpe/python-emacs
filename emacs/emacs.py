"""Interface with Emacs and run commands."""

from typing import Optional, Union, Sequence, List, Tuple
import os
import subprocess as sp
import json
from contextlib import contextmanager
from tempfile import TemporaryDirectory
import logging

from .elisp import Expr, E, get_src
from .elisp.exprs import StrOrExprOrList


def make_cmd(*parts: Union[str, Sequence[str], None]) -> List[str]:
	"""Concatenate arguments or lists of arguments to make command."""
	cmd = []

	for part in parts:
		if isinstance(part, str):
			cmd.append(part)
		elif part is not None:
			cmd.extend(part)

	return cmd


class EmacsBase:
	"""Abstract base class for an interface to GNU Emacs.

	Attributes
	----------
	cmd
		Command to run with each invocation.
	logger
		Logger instance.
	"""
	cmd: Tuple[str]
	logger: logging.Logger

	def __init__(self, cmd: Sequence[str], logger: Optional[logging.Logger] = None):
		self.cmd = tuple(cmd)
		self.logger = logging.getLogger(__name__) if logger is None else logger

	def run(self, args: Sequence[str], check: bool = True) -> sp.CompletedProcess:
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args
			Arguments to run command with.
		check
			Check the return code is zero.

		Raises
		------
		subprocess.CalledProcessError
			If ``check=True`` and return code is nonzero.

		Returns
		-------
		subprocess.CompletedProcess
			Completed process object.
		"""
		cmd = [*self.cmd, *args]

		self.logger.info(cmd)
		result = sp.run(cmd, check=False, stdout=sp.PIPE, stderr=sp.PIPE)

		if result.stderr:
			self.logger.warning(result.stderr.decode())
		if result.stdout:
			self.logger.debug(result.stdout.decode())

		if check:
			result.check_returncode()

		return result

	def eval(self, source: StrOrExprOrList, **kwargs) -> sp.CompletedProcess:
		"""Evaluate Elisp source code and return output.

		Parameters
		----------
		source
			Elisp code. If a list of strings/expressions will be enclosed in ``progn``.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		subprocess.CompletedProcess
			Completed process object.
		"""
		source = str(get_src(source))
		return self.run(['--eval', source], **kwargs)

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

	def _json_from_tmpfile(self, expr: StrOrExprOrList):
		"""Write result of evaluating expression to temporary file and parse as JSON."""
		with self._tmpfile() as tmpfile:
			self.write_result(expr, tmpfile)
			with open(tmpfile) as f:
				return json.load(f)

	def getresult_raw(self, source: StrOrExprOrList) -> str:
		"""Evaluate Elisp code and return the string representation of the result.

		Parameterrun command withs
		----------
		source
			Elisp code to evaluate.
		"""
		raise NotImplementedError()

	def getresult(self, source: StrOrExprOrList, is_json: str = False):
		"""Evaluate Elisp code and return the result as a Python value.

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
		"""
		expr = get_src(source)

		if not is_json:
			expr = E.progn(
				E.require(E.Q('json')),
				E.json_encode(expr)
			)

		return self._json_from_tmpfile(expr)


class EmacsBatch(EmacsBase):
	"""Interface to Emacs program using ``emacs --batch``.

	Parameters
	----------
	cmd
		Base command to run. Name or path of emacs executable plus optionally any additional
		arguments.
	args
		Additional arguments to add to ``cmd``.
	"""

	def __init__(self,
	             cmd: Union[str, Sequence[str]] = 'emacs',
	             *,
	             args: Optional[Sequence[str]] = None,
	             logger: Optional[logging.Logger] = None,
	             ):

		cmd = make_cmd(cmd, '--batch', args)
		EmacsBase.__init__(self, cmd, logger)


class EmacsClient(EmacsBase):
	"""Interface to running Emacs server using ``emacsclient``.

	Parameters
	----------
	cmd
		Base command to run. Name or path of emacsclient executable plus optionally any additional
		arguments.
	args
		Additional arguments to add to ``cmd``.
	server
		Name of server to connect to.
	"""

	def __init__(self,
	             cmd: Union[str, Sequence[str]] = 'emacsclient',
	             *,
	             args: Optional[Sequence[str]] = None,
	             server: Optional[str] = None,
	             logger: Optional[logging.Logger] = None,
	             ):

		cmd = make_cmd(cmd, ['-s', server] if server is not None else None, args)
		EmacsBase.__init__(self, cmd, logger)
