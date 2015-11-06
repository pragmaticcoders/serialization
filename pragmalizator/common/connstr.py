# -*- Mode: Python; test-case-name: pragmalizator.test.test_common_connstr -*-
# vi:si:et:sw=4:sts=4:ts=4

import re

_regexp = re.compile(r"""
^
  (?P<protocol>\w+)       # protocol
  ://
  (                       # optional @ section
    (?P<user>\w+)
    (:(?P<password>\w+))? # optional password
  @)?
  (?P<host>[^:]+)         # host or path
  (:(?P<port>\d+))?       # optional port number
$
""", re.VERBOSE)


def parse(connstr):
    global _regexp
    match = _regexp.search(connstr)
    if not match:
        raise ValueError("'%s' is not a valid connection string" %
                         (connstr, ))
    resp = dict()
    for key in ['protocol', 'user', 'password', 'host']:
        resp[key] = match.group(key)
    resp['port'] = match.group('port') and int(match.group('port'))

    return resp
