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
import collections
import functools
import sys
import uuid

from zope.interface import implements
from twisted.internet import reactor
from twisted.python import failure
from twisted.trial import unittest, util
from twisted.scripts import trial

from feat.database import emu as database
from feat.agencies import agency, journaler, message, recipient
from feat.agencies.messaging import emu, rabbitmq
from feat.agents.base import agent
from feat.common import log, defer, decorator, journal, time, signal

from feat.interface.generic import ITimeProvider
from feat.agencies.messaging.interface import ISink
from feat.agents.application import feat


from . import factories
from twisted.trial.unittest import FailTest

try:
    _getConfig = trial.getConfig
except AttributeError:
    # trial.getConfig() is only available when using flumotion-trial
    _getConfig = dict

log.init('test.log')


def delay(value, delay):
    '''Returns a deferred whose callback will be triggered
    after the specified delay with the specified value.'''
    d = defer.Deferred()
    time.callLater(delay, d.callback, value)
    return d


def break_chain(value):
    '''Breaks a deferred callback chain ensuring the rest will be called
    asynchronously in the next reactor loop.'''
    return delay_callback(value, 0)


def delay_errback(failure, delay):
    '''Returns a deferred whose errback will be triggered
    after the specified delay with the specified value.'''
    d = defer.Deferred()
    time.callLater(delay, d.errback, failure)
    return d


def break_errback_chain(failure):
    '''Breaks a deferred errback chain ensuring the rest will be called
    asynchronously in the next reactor loop.'''
    return delay_errback(failure, 0)


delay_callback = delay
break_callback_chain = break_chain


def attr(*args, **kwargs):
    """Decorator that adds attributes to objects.

    It can be used to set the 'slow', 'skip', or 'todo' flags in test cases.
    """

    def wrap(func):
        for name in args:
            # these are just True flags:
            setattr(func, name, True)
        for name, value in kwargs.items():
            setattr(func, name, value)
        return func
    return wrap


class TestCase(unittest.TestCase, log.LogProxy, log.Logger):

    implements(ITimeProvider)

    log_category = "test"

    # define names of class variables here, which values can be change
    # with the @attr decorator
    configurable_attributes = []
    skip_coverage = False

    def __init__(self, methodName=' impossible-name '):
        log_keeper = log.get_default() or log.FluLogKeeper()
        log.LogProxy.__init__(self, log_keeper)
        log.Logger.__init__(self, self)

        # Twisted changed the TestCase.__init__ signature several
        # times.
        #
        # In versions older than 2.1.0 there was no __init__ method.
        #
        # In versions 2.1.0 up to 2.4.0 there is a __init__ method
        # with a methodName kwarg that has a default value of None.
        #
        # In version 2.5.0 the default value of the kwarg was changed
        # to "runTest".
        #
        # In versions above 2.5.0 God only knows what's the default
        # value, as we do not currently support them.
        import inspect
        if not inspect.ismethod(unittest.TestCase.__init__):
            # it's Twisted < 2.1.0
            unittest.TestCase.__init__(self)
        else:
            # it's Twisted >= 2.1.0
            if methodName == ' impossible-name ':
                # we've been called with no parameters, use the
                # default parameter value from the superclass
                defaults = inspect.getargspec(unittest.TestCase.__init__)[3]
                methodName = defaults[0]
            unittest.TestCase.__init__(self, methodName=methodName)

        self.log_name = self.id()

        # Skip slow tests if '--skip-slow' option is enabled
        if _getConfig().get('skip-slow'):
            if self.getSlow() and not self.getSkip():
                self.skip = 'slow test'

        # Handle configurable attributes
        for attr in self.configurable_attributes:
            value = util.acquireAttribute(self._parents, attr, None)
            if value is not None:
                setattr(self, attr, value)

    def assert_not_skipped(self):
        if self.skip_coverage and sys.gettrace():
            raise unittest.SkipTest("Test Skipped during coverage")

    def setUp(self):
        log.test_reset()
        self.assert_not_skipped()
        # Scale time if configured
        scale = util.acquireAttribute(self._parents, 'timescale', None)
        if scale is not None:
            time.scale(scale)
        else:
            time.reset()
        self.info("Test running with timescale: %r", time._get_scale())

    def getSlow(self):
        """
        Return whether this test has been marked as slow. Checks on the
        instance first, then the class, then the module, then packages. As
        soon as it finds something with a C{slow} attribute, returns that.
        Returns C{False} if it cannot find anything.
        """

        return util.acquireAttribute(self._parents, 'slow', False)

    def wait_for(self, check, timeout, freq=0.5, kwargs=dict()):
        d = time.wait_for_ex(check, timeout, freq=freq, kwargs=kwargs,
                             logger=self)
        d.addErrback(lambda f: self.fail(f.value))
        return d

    def is_agency_idle(self, agency):
        return all([agent.is_idle() for agent in agency.get_agents()])

    @defer.inlineCallbacks
    def wait_agency_for_idle(self, agency, timeout, freq=0.5):
        try:
            check = lambda: self.is_agency_idle(agency)
            yield self.wait_for(check, timeout, freq)
        except unittest.FailTest:
            for agent in agency.get_agents():
                activity = agent.show_activity()
                if activity is None:
                    continue
                self.info(activity)
            raise

    def cb_after(self, arg, obj, method):
        '''
        Returns defered fired after the call of method on object.
        Can be used in defered chain like this:

        d.addCallback(doSomeStuff)
        d.addCallback(self._cb_after, obj=something, method=some_method)
        d.addCallback(jobAfterCallOfSomeMethod)

        This will fire last callback after something.some_method has been
        called.
        Parameter passed to the last callback is either return value of
        doSomeStuff, or, if this is None, the return value of stubbed method.
        '''
        old_method = obj.__getattribute__(method)
        d = defer.Deferred()

        def new_method(*args, **kwargs):
            obj.__setattr__(method, old_method)
            ret = old_method(*args, **kwargs)
            cb_arg = arg or (not isinstance(ret, defer.Deferred) and ret)
            reactor.callLater(0, d.callback, cb_arg)
            return ret

        obj.__setattr__(method, new_method)

        return d

    def assertCalled(self, obj, name, times=1, params=None):
        assert isinstance(obj, Mock), "Got: %r" % obj
        calls = obj.find_calls(name)
        times_called = len(calls)
        template = "Expected %s method to be called %d time(s), "\
                   "was called %d time(s)"
        self.assertEqual(times, times_called,\
                             template % (name, times, times_called))
        if params:
            for call in calls:
                self.assertEqual(len(params), len(call.args))
                for param, arg in zip(params, call.args):
                    self.assertTrue(isinstance(arg, param))

        return obj

    def assertIsInstance(self, _, klass):
        self.assertTrue(isinstance(_, klass),
             "Expected instance of %r, got %r instead" % (klass, _.__class__))
        return _

    def assertIs(self, expr1, expr2, msg=None):
        self.assertEqual(id(expr1), id(expr2),
                         msg or ("Expected same instances and got %r and %r"
                                 % (expr1, expr2)))

    def assertIsNot(self, expr1, expr2, msg=None):
        self.assertNotEqual(id(expr1), id(expr2),
                            msg or ("Expected different instances and got "
                                    "two %r" % (expr1, )))

    def assertAsyncEqual(self, chain, expected, value, *args, **kwargs):
        '''Adds an asynchronous assertion for equality to the specified
        deferred chain.

        If the chain is None, a new fired one will be created.

        The checks are serialized and done in order of declaration.

        If the value is a Deferred, the check wait for its result,
        if not it compare rightaway.

        If value is a callable, it is called with specified arguments
        and keyword WHEN THE PREVIOUS CALL HAS BEEN DONE.

        Used like this::

          d = defer.succeed(None)
          d = self.assertAsyncEqual(d, EXPECTED, FIRED_DEFERRED)
          d = self.assertAsyncEqual(d, EXPECTED, VALUE)
          d = self.assertAsyncEqual(d, 42, asyncDouble(21))
          d = self.assertAsyncEqual(d, 42, asyncDouble, 21)
          return d

        Or::

          return self.assertAsyncEqual(None, EXPECTED, FIRED_DEFERRED)
        '''

        def check(result):
            self.assertEqual(expected, result)
            return result

        if chain is None:
            chain = defer.succeed(None)

        return chain.addBoth(self._assertAsync, check, value, *args, **kwargs)

    def assertAsyncIterEqual(self, chain, expected, value, *args, **kwargs):

        def check(result):
            self.assertEqual(expected, list(result))
            return result

        if chain is None:
            chain = defer.succeed(None)

        return chain.addBoth(self._assertAsync, check, value, *args, **kwargs)

    def assertFails(self, exception_class, method, *args, **kwargs):
        d = method(*args, **kwargs)
        self.assertFailure(d, exception_class)
        return d

    @defer.inlineCallbacks
    def asyncEqual(self, expected, async_value):
        self.assertTrue(isinstance(async_value, defer.Deferred))
        value = yield async_value
        self.assertEqual(value, expected)

    @defer.inlineCallbacks
    def asyncIterEqual(self, expected, async_iter):
        self.assertTrue(isinstance(async_iter, defer.Deferred))
        iterator = yield async_iter
        self.assertTrue(isinstance(iterator, collections.Iterable))
        self.assertEqual(list(iterator), expected)

    @defer.inlineCallbacks
    def asyncErrback(self, error_class, fun, *args, **kwargs):
        result = fun(*args, **kwargs)
        self.assertTrue(isinstance(result, defer.Deferred))
        try:
            res = yield result
            self.fail("Expecting asynchronous error %s "
                      "and got result: %r" % (error_class.__name__, res))
        except Exception, e:
            if isinstance(e, FailTest):
                raise
            self.assertTrue(isinstance(e, error_class),
                            "Expecting asynchronous error %s "
                            "and got %s" % (error_class.__name__,
                                            type(e).__name__))

    def assertAsyncFailure(self, chain, errorKlasses, value, *args, **kwargs):
        '''Adds an asynchronous assertion for failure to the specified chain.

        If the chain is None, a new fired one will be created.

        The checks are serialized and done in order of declaration.

        If the value is a Deferred, the check wait for its result,
        if not it compare rightaway.

        If value is a callable, it is called with specified arguments
        and keyword WHEN THE PREVIOUS CALL HAS BEEN DONE.

        Used like this::

          d = defer.succeed(None)
          d = self.assertAsyncFailure(d, ERROR_CLASSES, FIRED_DEFERRED)
          d = self.assertAsyncFailure(d, ERROR_CLASSES, FUNCTION, ARG)
          d = self.assertAsyncFailure(d, [ValueError, TypeError], fun(21))
          d = self.assertAsyncFailure(d, [ValueError], fun, 21)
          return d

        '''

        def check(failure):
            if isinstance(errorKlasses, collections.Sequence):
                self.assertTrue(failure.check(*errorKlasses))
            else:
                self.assertTrue(failure.check(errorKlasses))
            return None # Resolve the error

        if chain is None:
            chain = defer.succeed(None)

        return chain.addBoth(self._assertAsync, check, value, *args, **kwargs)

    def assertAsyncRaises(self, chain, ErrorClass, fun, *args, **kwargs):

        def check(param):
            self.assertRaises(ErrorClass, fun, *args, **kwargs)
            return None # Resolve the error

        if chain is None:
            chain = defer.succeed(None)

        return chain.addBoth(check)

    def stub_method(self, obj, method, handler):
        handler = functools.partial(handler, obj)
        obj.__setattr__(method, handler)
        return obj

    def tearDown(self):
        log.test_reset()
        time.reset()
        signal.reset()

    ### ITimeProvider Methods ###

    def get_time(self):
        return time.time()

    ### Private Methods ###

    def _assertAsync(self, param, check, value, *args, **kwargs):
        if isinstance(param, failure.Failure):
            if param.check(AssertionError):
                param.raiseException()
        if isinstance(value, defer.Deferred):
            value.addBoth(check)
            return value

        if args is not None and callable(value):
            return self._assertAsync(param, check, value(*args, **kwargs))

        return check(value)


class Mock(object):

    def __init__(self):
        self._called = []

    def find_calls(self, name):
        return filter(lambda x: x.name == name, self._called)

    @staticmethod
    @decorator.simple_function
    def stub(method):

        def decorated(self, *args, **kwargs):
            call = MockCall(method.__name__, args, kwargs)
            self._called.append(call)

        return decorated

    @staticmethod
    @decorator.simple_function
    def record(method):

        def decorated(self, *args, **kwargs):
            call = MockCall(method.__name__, args, kwargs)
            self._called.append(call)
            return method(self, *args, **kwargs)

        return decorated


class MockCall(object):

    def __init__(self, name, args, kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class AgencyTestHelper(object):

    protocol_type = None
    protocol_id = None
    remote_id = None

    def setUp(self):
        self.agency = agency.Agency()
        self.guid = None
        self._messaging = emu.RabbitMQ()
        mesg = rabbitmq.Client(self._messaging, 'agency_queue')
        self._db = database.Database()
        writer = journaler.SqliteWriter(self)
        journal = journaler.Journaler()
        journal.configure_with(writer)

        d = writer.initiate()
        d.addCallback(defer.drop_param, self.agency.initiate,
                      self._db, journal, mesg)
        return d

    def setup_endpoint(self):
        '''
        Sets up the destination for tested component to send messages to.

        This returns:
         - endpoint: Recipient instance pointing to the queue above
                     (use it for reply-to fields)
         - queue: Queue instance we use may call .get() on to get
                  messages from components being tested

        @returns: tuple of endpoint, queue
        '''
        endpoint = recipient.Agent(str(uuid.uuid1()), 'lobby')
        messaging = self._messaging

        queue = messaging.define_queue(endpoint.key)
        messaging.define_exchange(endpoint.route, 'direct')
        messaging.create_binding(
            endpoint.route, endpoint.key, endpoint.key)
        return endpoint, queue

    def assert_queue_empty(self, queue, timeout=10):
        d = queue.get()
        d2 = delay(None, timeout)
        d2.addCallback(lambda _: self.assertFalse(d.called))
        d2.addCallback(d.callback)
        return d2

    # methods for handling documents

    def doc_factory(self, doc_class, **options):
        '''
        Builds document of given class and saves it to the database.

        @returns: Document with id and revision set
        @rtype:   subclass of feat.agents.document.Document
        '''
        document = factories.build(doc_class.type_name, **options)
        return self.agency._database.get_connection().save_document(document)

    # methods for sending and receiving custom messages

    def send_announce(self, manager):
        msg = message.Announcement()
        manager._get_medium().announce(msg)
        return manager

    def send_bid(self, contractor, bid=1):
        msg = message.Bid()
        msg.bids = [bid]
        contractor._get_medium().bid(msg)
        return contractor

    def send_refusal(self, contractor):
        msg = message.Refusal()
        contractor._get_medium().refuse(msg)
        return contractor

    def send_final_report(self, contractor):
        msg = message.FinalReport()
        contractor._get_medium().complete(msg)
        return contractor

    def send_cancel(self, contractor, reason=""):
        msg = message.Cancellation()
        msg.reason = reason
        contractor._get_medium().defect(msg)
        return contractor

    def recv_announce(self, expiration_time=None, traversal_id=None):
        msg = message.Announcement()
        self.guid = str(uuid.uuid1())
        msg.sender_id = self.guid
        msg.traversal_id = traversal_id or str(uuid.uuid1())

        return self.recv_msg(msg, expiration_time=expiration_time,
                             public=True)

    def recv_grant(self, _, update_report=None):
        msg = message.Grant()
        msg.update_report = update_report
        msg.sender_id = self.guid
        return self.recv_msg(msg).addCallback(lambda ret: _)

    def recv_rejection(self, _):
        msg = message.Rejection()
        msg.sender_id = self.guid
        return self.recv_msg(msg).addCallback(lambda ret: _)

    def recv_cancel(self, _, reason=""):
        msg = message.Cancellation()
        msg.reason = reason
        msg.sender_id = self.guid
        return self.recv_msg(msg).addCallback(lambda ret: _)

    def recv_ack(self, _):
        msg = message.Acknowledgement()
        msg.sender_id = self.guid
        return self.recv_msg(msg).addCallback(lambda ret: _)

    def recv_notification(self, result=None, traversal_id=None):
        msg = message.Notification()
        msg.traversal_id = traversal_id or str(uuid.uuid1())
        d = self.recv_msg(msg, key="dummy-notification")
        d.addCallback(defer.override_result, result)
        return d

    def recv_msg(self, msg, reply_to=None, key=None,
                  expiration_time=None, public=False):
        d = self.cb_after(arg=None, obj=self.agent._messaging,
                          method='on_message')

        msg.reply_to = reply_to or self.endpoint
        msg.expiration_time = expiration_time or (time.future(10))
        msg.protocol_type = self.protocol_type
        msg.protocol_id = self.protocol_id
        msg.message_id = str(uuid.uuid1())
        msg.receiver_id = self.remote_id

        key = 'dummy-contract' if public else self.agent._descriptor.doc_id
        shard = self.agent._descriptor.shard
        factory = recipient.Broadcast if public else recipient.Agent
        msg.recipient = factory(key, shard)
        self.agency._messaging.dispatch(msg)
        return d

    def reply(self, msg, reply_to, original_msg):
        d = self.cb_after(arg=None, obj=self.agent._messaging,
                          method='on_message')

        dest = recipient.IRecipient(original_msg)

        msg.reply_to = recipient.IRecipient(reply_to)
        msg.message_id = str(uuid.uuid1())
        msg.protocol_id = original_msg.protocol_id
        msg.expiration_time = time.future(10)
        msg.protocol_type = original_msg.protocol_type
        msg.receiver_id = original_msg.sender_id

        msg.recipient = dest
        self.agency._messaging.dispatch(msg)
        return d


class StubAgent(object):

    implements(ISink)

    def __init__(self):
        self.queue_name = str(uuid.uuid1())
        self.messages = []

    ### IChannelSink ###

    def get_agent_id(self):
        return self.queue_name

    def get_shard_id(self):
        return 'lobby'

    def on_message(self, msg):
        self.messages.append(msg)


@feat.register_agent('descriptor')
class DummyAgent(agent.BaseAgent, Mock):

    # We don't want a SetupMonitoring task in all the tests
    need_local_monitoring = False

    def __init__(self, medium):
        agent.BaseAgent.__init__(self, medium)
        Mock.__init__(self)

    @Mock.record
    def initiate(self):
        pass

    @Mock.stub
    def shutdown(self):
        pass

    @Mock.stub
    def startup(self):
        pass

    @Mock.stub
    def unregister(self):
        pass


class DummyRecorderNode(journal.DummyRecorderNode, log.LogProxy, log.Logger):

    def __init__(self, test_case):
        journal.DummyRecorderNode.__init__(self)
        log.LogProxy.__init__(self, test_case)
        log.Logger.__init__(self, test_case)
