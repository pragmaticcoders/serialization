from zope.interface import Interface, Attribute
from serialization.common import enum


class Severity(enum.Enum):

    ok, warn, critical = range(3)


class IAlertFactory(Interface):

    name = Attribute('C{str} unique name of the service')
    persistent = Attribute('C{bool} flag saying if the alert should persist '
                           'in nagios config between restarts of the cluster')
    description = Attribute('C{str} optional description to use in nagios')

    def __call__(hostname, agent_id, status_info, severity=None):
        '''Construct IAlert'''


class IAlert(Interface):

    name = Attribute('C{str} unique name of the service')
    hostname = Attribute('Host name running the agent who raised the alert')
    status_info = Attribute('C{str} optional string specifing more details.')
    agent_id = Attribute("C{str} agent_id who raised the alert")
    severity = Attribute('L{Severity}')
