# F3AT - Flumotion Asynchronous Autonomous Agent Toolkit
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# See "LICENSE.GPL" in the source distribution for more information.

# Headers in this file shall remain intact.
from future import standard_library
standard_library.install_aliases()
from builtins import map

import re
import io
import traceback
import types
import sys

from serialization.common import log, decorator, reflect
from serialization.extern.log import log as xlog


@decorator.simple_function
def log_errors(function):
    """Logs the exceptions raised by the decorated function
    without interfering. For debugging purpose."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException as e:
            handle_exception(None, e, "Exception in function %s",
                             reflect.canonical_name(function))
            raise

    return wrapper


@decorator.simple_function
def print_errors(function):
    """Prints the exceptions raised by the decorated function
    without interfering. For debugging purpose."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException as e:
            print ("Exception raise calling %s: %s"
                   % (reflect.canonical_name(function),
                      get_exception_message(e)))
            raise

    return wrapper


class FeatError(Exception):
    """
    An exception that keep information on the cause of its creation.
    The cause may be other exception or a Failure.
    """

    default_error_code = None
    default_error_name = None

    def __init__(self, *args, **kwargs):
        self.data = kwargs.pop('data', None)
        self.cause = kwargs.pop('cause', None)
        default_code = self.default_error_code
        default_name = self.default_error_name or self.__class__.__name__
        self.error_code = kwargs.pop('code', default_code)
        self.error_name = kwargs.pop('name', default_name)

        if args and isinstance(args[0], str):
            # Exception don't like passing them unicode strings
            # as a message. Here we do our best to encode it
            try:
                encoded = args[0].encode('utf8')
            except:
                encoded = args[0].encode('ascii', 'replace')
            args = (encoded, ) + args[1:]

        Exception.__init__(self, *args, **kwargs)

        self.cause_details = None
        self.cause_traceback = None

        try:
            from twisted.python.failure import Failure
        except ImportError:
            Failure = None

        if self.cause:
            if isinstance(self.cause, Exception):
                self.cause_details = get_exception_message(self.cause)
            elif Failure and isinstance(self.cause, Failure):
                self.cause_details = get_failure_message(self.cause)
            else:
                self.cause_details = "Unknown"

            if Failure and isinstance(self.cause, Failure):
                f = self.cause
                self.cause = f.value
                try:
                    self.cause_traceback = f.getTraceback()
                except:
                    # Ignore failure.NoCurrentExceptionError
                    pass
            elif Failure:
                try:
                    f = Failure()
                    if f.value == self.cause:
                        self.cause_traceback = f.getTraceback()
                except:
                    # Ignore failure.NoCurrentExceptionError
                    pass


class NonCritical(FeatError):
    '''Subclasses of this exception are logged with custom log_level
    and message. Use this to create exceptions which are not errors
    but an expected valid behaviour of some protocol.
    '''
    log_level = 4
    log_line_template = "Noncritical error occured: %(class_name)s"


def get_exception_message(exception):
    try:
        msg = xlog.getExceptionMessage(exception)
    except IndexError:
        # log.getExceptionMessage do not like exceptions without messages ?
        msg = type(exception).__name__
    if isinstance(exception, FeatError):
        details = exception.cause_details
        if details:
            msg += "; CAUSED BY " + details
    return msg


def get_failure_message(failure):
    try:
        msg = xlog.getFailureMessage(failure)
    except KeyError:
        # Sometime happen for strange error, just when we realy need a message
        error_type = failure.type
        if isinstance(error_type, types.TypeType):
            error_type = error_type.__name__
        msg = "%s %s" % (error_type, failure.getErrorMessage())
    exception = failure.value
    if isinstance(exception, FeatError):
        details = exception.cause_details
        if details:
            msg += "; CAUSED BY " + details
    return msg


def get_exception_traceback(exception=None, cleanup=False):
    #FIXME: Only work if the exception was raised in the current context
    io = io.StringIO()
    traceback.print_exc(limit=30, file=io)
    tb = io.getvalue()
    if not tb:
        tb = ("Exception has no traceback information. \n",
              "This can happen for 2 known reasons: \n",
              "1) error.handle_exception is called ",
              "getting passed as a parameter exception instance extracted ",
              "from the failure. Solution: use error.handle_failure()\n",
              "2) error.handle_exception is called with an exception ",
              "created by hand like 'return TypeError(msg)'. You should ",
              "raise this exception instead.")
    if cleanup:
        tb = clean_traceback(tb)

    if isinstance(exception, FeatError):
        if exception.cause_traceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            ctb = exception.cause_traceback
            if cleanup:
                ctb = clean_traceback(ctb)
            tb += ctb

    return tb


def get_failure_traceback(failure, cleanup=False):
    if isinstance(failure.type, str):
        return ""

    io = io.StringIO()
    tb = failure.getTraceback()
    if cleanup:
        tb = clean_traceback(tb)
    print >> io, tb
    exception = failure.value
    if exception and isinstance(exception, FeatError):
        if exception.cause_traceback:
            print >> io, "\n\nCAUSED BY:\n\n"
            tb = exception.cause_traceback
            if cleanup:
                tb = clean_traceback(tb)
            print >> io, tb

    return io.getvalue()


def clean_traceback(tb):
    '''Fixes up the traceback to remove the from the file paths the part
    preceeding the project root.
    @param tb: C{str}
    @rtype: C{str}'''
    prefix = __file__[:__file__.find("serialization/common/error.py")]
    regex = re.compile("(\s*File\s*\")(%s)([a-zA-Z-_\. \\/]*)(\".*)"
                       % prefix.replace("\\", "\\\\"))

    def cleanup(line):
        m = regex.match(line)
        if m:
            return m.group(1) + ".../" + m.group(3) + m.group(4)
        else:
            return line

    return '\n'.join(map(cleanup, tb.split('\n')))


def handle_failure(source, failure, template, *args, **kwargs):
    logger = _get_logger(source)

    info = kwargs.get("info", None)
    debug = kwargs.get("debug", None)

    category = logger.log_category
    if category is None:
        category = 'serialization'
    if failure.check(NonCritical):
        e = failure.value
        msg = failure.getErrorMessage()
        msg = (e.log_line_template %
               dict(class_name=type(failure.value), msg=msg))
        logger.logex(e.log_level, msg, ())
    elif xlog.getCategoryLevel(category) in [xlog.LOG, xlog.DEBUG]:
        msg = get_failure_message(failure)
        cleanup = kwargs.get("clean_traceback", False)
        tb = get_failure_traceback(failure, cleanup)
        logger.error(template + ": %s\n%s", *(args + (msg, tb)))
    else:
        msg = get_failure_message(failure)
        logger.error(template + ": %s", *(args + (msg, )))

    if log.verbose:
        if info:
            logger.info("Additional Information:\n%s", info)
        if debug:
            logger.debug("Additional Debug:\n%s", debug)


def handle_exception(source, exception, template, *args, **kwargs):
    logger = _get_logger(source)

    info = kwargs.get("info", None)
    debug = kwargs.get("debug", None)
    msg = get_exception_message(exception)

    category = logger.log_category
    if category is None:
        category = 'serialization'
    if isinstance(exception, NonCritical):
        e = exception
        msg = e.log_line_template % dict(class_name=type(exception), msg=msg)
        logger.logex(e.log_level, msg, ())
    elif xlog.getCategoryLevel(category) in [xlog.LOG, xlog.DEBUG]:
        cleanup = kwargs.get("clean_traceback", False)
        tb = get_exception_traceback(exception, cleanup)
        logger.error(template + ": %s\n%s", *(args + (msg, tb)))
    else:
        logger.error(template + ": %s", *(args + (msg, )))

    if log.verbose:
        if info:
            logger.info("Additional Information:\n%s", debug)
        if debug:
            logger.debug("Additional Debug:\n%s", debug)


def print_stack():
    traceback.print_stack(file=sys.stdout)


### private ###


def _get_logger(maybe_logger):
    if maybe_logger is None or not log.ILogger.providedBy(maybe_logger):
        return log.create_logger()
    return log.ILogger(maybe_logger)
