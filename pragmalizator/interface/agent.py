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
from zope.interface import Interface, Attribute
from pragmalizator.common import enum

from pragmalizator.database.interface import IDocument

__all__ = ["IAgentFactory", "IAgencyAgent", "IAgencyAgent", "IAgent",
           "AgencyAgentState", "Access", "Address", "Storage",
           "CategoryError"]


class CategoryError(RuntimeError):
    """
    Raised when categories don't match with the
    categories defined in the HostAgent.
    """


class Access(enum.Enum):
    '''
    If the machine can be accessed from outside
    '''

    none, public, private = range(3)


class Address(enum.Enum):
    '''
    If the machine network address can change or is fixed
    '''

    none, fixed, dynamic = range(3)


class Storage(enum.Enum):
    '''
    If the machine storage is reliable upon restart is shared amongst other
    machines in the same site.
    '''

    none, static, shared, volatile = range(4)


class IAgentFactory(Interface):
    '''Create an agent implementing L{IAgent}. Used by the agency when
    starting an agent.'''

    standalone = Attribute("bool. whether to run in standalone process")

    categories = Attribute("Dict. Access, Address and Storage")

    restart_strategy = Attribute(
        "L{pragmalizator.agents.common.monitor.RestartStrategy}")

    def __call__(medium, *args, **kwargs):
        pass

    def get_cmd_line(*args, **kwargs):
        '''
        Should be implemeneted for the stand alone agents. Returns the
        command line which need to be run to start the external process, its
        arguments and environment.
        @returns: Tuple of the format: (command, args, env).
        '''


class AgencyAgentState(enum.Enum):
    '''
     - not_initiated - Agent is not yet initialized.
     - initiating    - Agent is currently initializing.
     - initiated     - Initialize done.
     - starting_up   - Agent is starting up.
     - ready         - Agent has finished starting up and is ready.
     - disconnected  - Triggered when agency looses database or messaging
                       connection.
     - terminating   - Agent is going through termination procedure.
     - terminated    - Agent is terminated and unregistered.
    '''
    (not_initiated, initiating, initiated, starting_up,
     ready, disconnected, terminating, terminated) = range(8)


class IAgencyAgent(Interface):
    '''Agency part of an agent. Used as a medium by the agent
    L{IAgent} implementation.'''

    agent = Attribute("L{IAgent}")
    agency = Attribute("L{IAgency}")
    startup_failure = Attribute("Failure or NoneType")

    def remove_external_route(backend_id, **kwargs):
        pass

    def create_external_route(backend_id, **kwargs):
        pass

    def observe(callable, *args, **kwargs):
        """
        Observes the asynchronous method result.
        The callable may return Fiber or Deferred.
        Use it if you want to know keep the
        information about the result of the fiber without keeping the
        reference to the original object. This is usefull when dealing with
        transient object like Tasks, Managers, etc. Examples::

            observer = state.medium.observe(task.notify_finish)
            ....
            f = observer.notify_finish()
            (do sth with f)

            Synchronous methods:
            if not observer.active():
              res = oserver.get_result()

        @type fiber: L{pragmalizator.interface.fiber.IFiber}
        @rtype: L{pragmalizator.interface.fiber.IObserver}
        """

    def get_hostname():
        '''
        Return the host name we run on.
        '''

    def get_descriptor():
        '''
        Return the copy of the descriptor.
        '''

    def get_configuration():
        '''
        Return a copy of the agents metadocument with configuration.
        '''

    def update_descriptor(callable, *args, **kwargs):
        '''
        Schedule a descriptor update.
        The specified callable will be called when all pending descriptor
        updates are done with the last descriptor value and the specified
        arguments.
         - The callable can modify the descriptor and return a result.
         - The callable must be synchronous.
         - The callable cannot return a deferred or a fiber.
         - When the callable returns, the updated descriptor is saved.
         - The returned deferred is fired with the callable result.

        This method should be used instead of save_document because:
         - agency queue descriptor updates to be sure only one happen at a time
           preventing conflicts.
         - agency side of implementation needs to keep track of the changes.

        @param callable: Synchronous function that update a descriptor.
        @type callable: function
        @returns: Deferred
        '''

    def join_shard(shard_id):
        '''Joins shard with specified identifier.'''

    def leave_shard(shard_id):
        '''Leave the shard with specified identifier.'''

    def upgrade_agency(ugrade_cmd):
        '''Used by host agent to tell agency to shutdown all the agents
        and run external script.'''

    def register_interest(factory):
        '''Registers an interest in a contract or a request.'''

    def initiate_protocol(factory, *args, **kwargs):
        '''
        Initiates a contract or a request.
        Arguments varies in function of the specified factory.

        @rtype: L{IInitiator}
        @returns: Instance of protocols initiator
        '''

    def save_document(document):
        '''
        Save the document into the database. Document might have been loaded
        from the database before, or has just been constructed.

        If the doc_id
        property of the document is not set, it will be loaded from the
        database.

        @param document: Document to be saved.
        @type document: Subclass of L{pragmalizator.agents.document.Document}
        @returns: Deferred called with the updated Document (id and revision
                  set)
        '''

    def get_document(document_id):
        '''
        Download the document from the database and instantiate it.

        @param document_id: The id of the document in the database.
        @returns: The Deffered called with the instance representing downloaded
                  document.
        '''

    def reload_document(document):
        '''
        Fetch the latest revision of the document and update it.

        @param document: Document to update.
        @type document: Subclass of L{pragmalizator.agents.document.Document}.
        @returns: Deferred called with the updated instance.
        '''

    def delete_document(document):
        '''
        Marks the document in the database as deleted. The document
        returns in the deferred can still be used in the application.
        For example one can call save_document on it to bring it back.

        @param document: Document to be deleted.
        @type document: Subclass of L{pragmalizator.agents.document.Document}.
        @returns: Deferred called with the updated document (latest revision).
        '''

    def register_change_listener(filter, callback, **kwargs):
        '''
        Registers for receiving notifications about the document changes.
        @param filter: id of the document or a IViewFactory to use for
                       filtering
        @param callback: callable to be called, it will be called with the
                         following parametes:
                          - doc_id
                          - rev
                          - deleted (flag)
                          - own_change (flag saying if the notification was
                            triggered by the change done on the same
                            connection)
        @params kwargs: Optional keywords to be passed to the changes query.
        @return: None
        '''

    def cancel_change_listener(filter):
        '''
        Unregister agent from receiving the notifications about document
        changes.
        '''

    def query_view(factory, **options):
        '''
        Queries the database view.

        It only supports small part of CouchDB features. In production
        implementation the options are just passed to the query. This means
        that basicly everything is supported. In emu database implementation
        the only supported option is:
         - reduce C{boolean}: optionaly lets fetch the result of the map from
           the map-reduce view (skips the reduce part).
        In case you want to use more features of CouchDB you should implement
        them feat.agencies.emu.database.Database, and test their intergration
        in pragmalizator.test.integration.test_idatabase_client.

        @param factory: View factory to query.
        @type factory: L{pragmalizator.interface.view.IViewFactory}
        @param options: Dictionary of parameters to pass to the query.
        @return: C{list} of the results.
        '''

    def get_database():
        '''
        Returns the IDatabaseClient instance connected to the same database
        as the agent. Use it to gain direct access to all connection methods
        without the necessity to go through multiple level of delegation.
        '''

    def terminate():
        '''
        Performs all the necessary steps to end the life of the agent in a
        gentle way. The termination process consits of following steps:

         1. Revoke all interests.
         2. Terminate all retrying protocols.
         3. Kill all protocols (with making them expire instantly).
         4. Run the IAgent.shutdown() and wait for it to finish.
            perform agent-side shutdown part common to all agents.
         5. Remove agents descriptor from the database.
         6. Delete the agents queue.

        @returns: Deferred.
        '''

    def terminate_hard():
        '''
        Performs all the less gentle form of the agents shutdown. This type
        of shutdown is the same as if the descriptor of the agent has been
        modified, or the agency process received the SIGTERM signal.
        The only callback called on the agent-side during this procedure
        is on_killed(), we are not sending goodbyes to the partners, nor
        touching the descriptor or the queue.

         1. Revoke all interests.
         2. Terminate all retrying protocols.
         3. Kill all protocols (with making them expire instantly).
         4. Run the IAgent.on_killed() and wait for it to finish.

        @returns: Deferred.
        '''

    def get_mode(component):
        '''
        Get the mode to run given component.
        '''

    def wait_for_state(state):
        '''
        Wait for for specific state
        '''

    def get_machine_state():
        '''
        Returns the current state
        '''

    def call_next(method, *args, **kwargs):
        '''
        Calls the method outside the current execution chain.
        @returns: The call id which can be used to cancel the call.
        '''

    def call_later(time_left, method, *args, **kwargs):
        '''
        Calls the method in future.
        @returns: The call id which can be used to cancel the call.
        '''

    def cancel_delayed_call(call_id):
        '''
        Cancels the delayed call.
        '''

    def is_connected():
        '''
        @return: Flag saying if RabbitMQ and CouchDB connection is established
        @rtype: C{bool}
        '''

    def get_canceller():
        '''
        @return: a canceller that cancel a fiber when the agent state changes.
        @rtype: fiber.ICancellable
        '''

    def get_base_gateway_url():
        '''
        @return: C{ctr} base url of gateway to access.
        '''


class IAgent(Interface):
    '''
    Agent interface exposed to the agency. Methods defined here are called
    by the AgencyAgent on different stages of life of the agent.
    '''

    def initiate_agent(**kwargs):
        '''
        Called after the agent is registered to an agency.
        Keywords are passed to IAgency.start_agent(). This method calls
        initiate() methods of every class in MRO. The keywords are passed
        to initiate method with matching names (for this reason there is no
        positional arguments).
        '''

    def startup_agent():
        '''
        Called when initiate_agent has finished.
        Calls startup() methods from MRO in reverse-mro order.
        '''

    def shutdown_agent():
        """
        Called after agency decides to terminate the agent.
        Agent code should take care to notify all it's his contractors
        that the collaboration is over.
        Calls shutdown() methods from MRO in reverse-mro order.
        """

    def on_agent_killed():
        '''
        Called as part of the SIGTERM handler. This type of shutdown assumes
        that the monitoring agent will restart us somewhere.
        Calls on_killed() methods from MRO in reverse-mro order.
        '''

    def on_agent_disconnect():
        '''
        Called when agency gets disconnected from messaging or database
        server.
        Calls on_disconnect() methods from MRO in reverse-mro order.
        '''

    def on_agent_reconnect():
        '''
        Called when both connections to messaging and database are restored.
        Calls on_reconnect() methods from MRO  in reverse-mro order.
        '''

    def get_description():
        '''
        Override this to give an description specific for the instance of the
        agent. This will be shown in the the /agents section of the gateway.
        '''


class IDescriptor(IDocument):
    '''Interface implemented by the documents holding persitent state of the
    agent'''

    shard = Attribute('C{unicode} Shard the agent runs in')
    instance_id = Attribute('C{int} counter of agent incarnation')
    resources = Attribute('C{dict} name -> IAllocatedResource '
                          'resources allocated by HA for this agent')
    under_restart = Attribute('C{bool} flag saying that the agent is '
                              'being restarted right now my the monitor')
    partners = Attribute('C{list} of IPartner')


class IPartner(Interface):

    recipient = Attribute('IRecipient of the agent on the other side')
    allocation_id = Attribute('C{int} id of the allocation representing this '
                              'partnership (or None)')
    role = Attribute('C{unicode} optional role identifier')

    def initiate(agent):
        """After returning a synchronous result or when the returned fiber
        is finished the partner is stored to descriptor."""

    def on_shutdown(agent):
        pass

    def on_goodbye(agent, brothers):
        '''
        Called when the partner goes through the termination procedure.

        @param brothers: The list of the partner of the same class
                         of the agent.
        '''

    def on_breakup(agent):
        '''
        Called when we have successfully broken up with the partner.
        '''

    def on_died(agent, brothers, monitor):
        '''
        Called by the monitoring agent, when he detects that the partner has
        died. If your handler is going to solve this problem return the
        L{pragmalizator.agents.base.partners.ResponsabilityAccepted} instance.

        @param brothers: Same as in on_goodbye.
        @param monitor: IRecipient of monitoring agent who notified us about
                        this unfortunate event
        '''

    def on_restarted(agent, old_recipient):
        '''
        Called after the partner is restarted by the monitoring agent.
        After returning a synchronous result or when the returned fiber
        is finished the partner is stored to descriptor.
        '''

    def on_buried(agent, brothers=None):
        '''
        Called when all the hope is lost. Noone took the responsability for
        handling the agents death, and monitoring agent failed to restart it.

        @param brothers: The list of the partner of the same class
                         of the agent.
        '''


class IMonitorAgent(IAgent):
    '''Point of defining this interface is to be have a interface type to
    adapt agent class to IModel without the instance checks. Without this
    adaptation will not work after reloading the pragmalizator module.'''


class IAlertAgent(IAgent):
    '''Point of defining this interface is to be have a interface type to
    adapt agent class to IModel without the instance checks. Without this
    adaptation will not work after reloading the pragmalizator module.'''

    def get_alerts():
        '''Returns list of ReceivedAlerts representing all the services
        known to this agent'''

    def get_raised_alerts():
        '''Returns a list of ReceivedAlerts instances for the services which
        raised the alarm.'''

    def generate_nagios_service_cfg():
        '''Returns a body of the configuraton file for the services currently
        monitored by the agent.'''
