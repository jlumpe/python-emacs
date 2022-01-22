"""Interface with Emacs and run commands."""

from abc import ABC, abstractmethod
from typing import Optional, Union, Sequence, List, Tuple, Any, Iterable
import os
import subprocess as sp
import json
from tempfile import mkstemp
import logging

from . import elisp as el
from .elisp import E, Expr
from .elisp.exprs import StrOrExprOrList
from .elisp.util import unescape_emacs_string


def make_cmd(*parts: Union[str, Sequence[str], None]) -> List[str]:
	"""Concatenate arguments or lists of arguments to make command."""
	cmd = []

	for part in parts:
		if isinstance(part, str):
			cmd.append(part)
		elif part is not None:
			cmd.extend(part)

	return cmd


class ElispException(Exception):
	"""An exception caught in Emacs while evaluating an expression.

	Attributes
	----------
	message
		Error message, from ``error-message-string``.
	symbol
		Error symbol, the ``car`` of the caught error object.
	data
		Error data, the ``cdr`` of the caught error object.
	expr
		The expression that was being evaluated.
	proc
		Completed process object.
	"""
	message: str
	symbol: str
	data: Any
	expr: Expr
	proc: sp.CompletedProcess

	def __init__(self, message: str, symbol: str, data, expr: Expr, proc: sp.CompletedProcess):
		super(ElispException, self).__init__(message)
		self.message = message
		self.symbol = symbol
		self.data = data
		self.expr = expr
		self.proc = proc


def el_encode_json(expr: Expr) -> Expr:
	"""Elisp snippet to encode value as JSON."""
	return E.progn(
		E.require(E.json.q),
		E.json_encode(expr)
	)


def el_catch_err_json(expr: Expr, encoded: bool = False) -> Expr:
	"""Elisp snippet to catch errors and return the error message as encoded JSON."""
	if encoded:
		expr_enc = expr
	else:
		expr_enc = E.json_encode(expr)

	return el.Raw(f'''
	(let
	  (
	    (value-enc nil)
	    (err-enc "null")
	  )
	  (require 'json)
	  (setq value-enc
	    (condition-case err
	      {expr_enc!s}
	      (error
	        (setq err-enc
	          (json-encode-plist
	            (list
	              :symbol (car err)
	              :data (cdr err)
	              :msg (error-message-string err)
	            )
	          )
	        )
	        "null"
	      )
	    )
	  )
	  (format "{{\\"value\\": %s, \\"error\\": %s}}" value-enc err-enc)
	)
	''')


class EmacsBase(ABC):
	"""Abstract base class for an interface to GNU Emacs.

	Attributes
	----------
	cmd
		Command to run with each invocation.
	logger
		Logger instance (not yet implemented).
	"""
	cmd: Tuple[str]
	logger: logging.Logger

	def __init__(self, cmd: Sequence[str], logger: Optional[logging.Logger] = None):
		self.cmd = tuple(cmd)
		self.logger = logging.getLogger(__name__) if logger is None else logger

	def run(self,
	        args: Sequence[str],
	        *,
	        check: bool = True,
	        run_kw=None,
	        ) -> sp.CompletedProcess:
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args
			Arguments to run command with.
		check
			Check the return code is zero.
		run_kw
			Keyword arguments to pass to :func:`subprocess.run`.

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

		if run_kw is None:
			run_kw = dict()

		return sp.run(cmd, check=check, stdout=sp.PIPE, stderr=sp.PIPE, **run_kw)

	def _eval(self, expr: Expr, extra_args=None, **kw):
		"""Evaluate the expression as-is."""
		if extra_args is None:
			extra_args = ()

		args = ['--eval', str(expr), *extra_args]
		return self.run(args, **kw)

	@abstractmethod
	def _read_str_stdout(self, expr: Expr, **kw):
		"""Evaluate elisp code, read resulting string from stdout.

		Parameters
		----------
		expr
			Elisp code to evaluate. Must evaluate to string.
		kw
			Passed to :meth:`eval`.
		"""
		raise NotImplementedError()

	def _read_str_file(self, expr: Expr, path = None, **kw):
		"""Evaluate elisp code, writing resulting string to a file and reading from Python.

		Parameters
		----------
		expr
			Elisp code to evaluate. Must evaluate to string.
		path
			File to write to. If None will use temporary file.
		kw
			Passed to :meth:`eval`.
		"""
		if path is None:
			(fh, path) = mkstemp()
			needs_del = True
		else:
			path = str(path)
			needs_del = False

		try:
			src2 = E.with_temp_file(path, E.insert(expr))

			cp = self._eval(src2, **kw)

			with open(path) as f:
				data = f.read()

			return cp, data

		finally:
			if needs_del:
				try:
					os.unlink(path)
				except FileExistsError:
					pass

	def _read_str(self, expr: Expr, tmpfile: bool = False, **kw):
		"""Evaluate Elisp code and get the resulting string.

		Parameters
		----------
		expr
			Elisp code to evaluate. Must result in a string.
		tmpfile
			Read result through temporary file instead of stdout.
		kw
			Passed to :meth:`_eval`.
		"""
		if tmpfile:
			return self._read_str_file(expr, **kw)
		else:
			return self._read_str_stdout(expr, **kw)

	def eval(self,
	         src: StrOrExprOrList,
	         *,
	         catch_errors: bool = True,
	         ret: Optional[str] = 'value',
	         is_json: bool = False,
	         extra_args: Optional[Iterable[str]] = None,
	         tmpfile: bool = False,
	         **kw):
		"""Evaluate Elisp source code.

		Parameters
		----------
		src
			Elisp code. If a list of strings/expressions will be enclosed in ``progn``.
		catch_errors
			Catch errors evaluating the expression in Emacs and raise an :exc:`.ElispException` in
			Python.
		ret
			What to return. ``'value'`` returns the value of the evaluated expression (must be
			something that can be JSON-encoded using ``(json-encode)``. ``'subprocess'`` returns the
			:class:`subprocess.CompletedProcess`` of the command that was run (can be used to get
			the raw output). ``'both'`` returns a tuple ``(value, process)``. ``'none'`` or ``None``
			returns nothing. Use ``subprocess`` or ``none`` to avoid processing a potentially large
			amount of output you don't care about.
		extra_args
			Additional arguments to pass to command.
		tmpfile
			Read result through temporary file instead of stdout. This may avoid certain issues
			``emacsclient`` has when printing large amounts of output, or if the expression also
			has the side effect of printing to stdout.
		is_json
			If the result of evaluating ``src`` is already a json-encoded string that should be
			decoded.
		kw
			Passed to :meth:`run`.

		Raises
		------
		.ElispException
			If ``catch_errors=True`` and there is an error in Emacs when evaluating the expression.
		subprocess.CalledProcessError
			If ``check=True`` and return code is nonzero.

		Returns
		-------
		Any
			See the ``ret`` argument.
		"""
		if ret == 'value':
			ignore_value = False
		elif ret == 'process':
			ignore_value = True
		elif ret == 'both':
			ignore_value = False
		elif ret == 'none' or ret is None:
			ignore_value = True
		else:
			raise ValueError(f'ret argument must be one of "value", "process", "both", or "none", got {ret!r}')

		expr = el.get_src(src)
		inner_expr = expr
		eval_kw = dict(**kw, extra_args=extra_args)
		read_kw = dict(**eval_kw, tmpfile=tmpfile)

		if catch_errors:
			if ignore_value:
				expr = E.progn(expr, el.nil)  # Don't encode/output result
			expr = el_catch_err_json(expr, is_json)

			cp, s = self._read_str(expr, **read_kw)

			data = json.loads(s)
			err = data['error']
			value = data['value']

			if err is not None:
				raise ElispException(err['msg'], err['symbol'], err['data'], inner_expr, cp)

		elif ignore_value:
			cp = self._eval(expr, **eval_kw)
			value = None

		else:
			if not is_json:
				expr = el_encode_json(expr)

			cp, s = self._read_str(expr, **read_kw)
			value = json.loads(s)

		if ret == 'value':
			return value
		elif ret == 'process':
			return cp
		elif ret == 'both':
			return (value, cp)
		elif ret == 'none' or ret is None:
			return None
		else:
			assert False


class EmacsBatch(EmacsBase):
	"""Interface to Emacs program using ``emacs --batch``.

	Parameters
	----------
	cmd
		Base command to run. Name or path of emacs executable.
	args
		Additional arguments to add to ``cmd``.
	"""

	def __init__(self,
	             cmd: str = 'emacs',
	             *,
	             args: Optional[Sequence[str]] = None,
	             logger: Optional[logging.Logger] = None,
	             ):
		cmd = make_cmd(cmd, '--batch', args)
		EmacsBase.__init__(self, cmd, logger)

	def _read_str_stdout(self, expr: Expr, **kw):
		expr = E.princ(expr)
		cp = self._eval(expr, **kw)
		data = cp.stdout.decode()
		return cp, data


class EmacsClient(EmacsBase):
	"""Interface to running Emacs server using ``emacsclient``.

	Parameters
	----------
	cmd
		Base command to run. Name or path of emacsclient executable.
	args
		Additional arguments to add to ``cmd``.
	server
		Name of server to connect to.
	"""

	def __init__(self,
	             cmd: str = 'emacsclient',
	             *,
	             args: Optional[Sequence[str]] = None,
	             server: Optional[str] = None,
	             logger: Optional[logging.Logger] = None,
	             ):
		cmd = make_cmd(cmd, ['-s', server] if server is not None else None, args)
		EmacsBase.__init__(self, cmd, logger)

	def _read_str_stdout(self, expr: Expr, **kw):
		cp = self._eval(expr, **kw)
		escaped = cp.stdout.decode()
		data = unescape_emacs_string(escaped.strip(), quotes=True)
		return cp, data
