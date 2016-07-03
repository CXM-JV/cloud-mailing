#!/usr/bin/env python
# Copyright 2015 Cedric RICARD
#
# This file is part of mf_v4.
#
# mf_v4 is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mf_v4 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with mf_v4.  If not, see <http://www.gnu.org/licenses/>.

import sys

from twisted.internet import protocol
from twisted.internet import ssl
from twisted.internet import defer
from twisted.internet import stdio
from twisted.mail import imap4
from twisted.protocols import basic
from twisted.python import util
from twisted.python import log

from ConfigParser import RawConfigParser

import import_cm_path
from cloud_mailing.common.db_common import Db
from handle_reports import handle_report

config = RawConfigParser()
config.read('collect_reports.ini')

imap_account = config.get('IMAP', 'login')
imap_pwd = config.get('IMAP', 'pwd')
imap_folder = config.get('IMAP', 'folder')
imap_server = config.get('IMAP', 'server')
mailing_ids = map(int, config.get('MAILING', 'ids').split(','))


class TrivialPrompter(basic.LineReceiver):
    from os import linesep as delimiter

    promptDeferred = None

    def prompt(self, msg):
        assert self.promptDeferred is None
        self.display(msg)
        self.promptDeferred = defer.Deferred()
        return self.promptDeferred

    def display(self, msg):
        self.transport.write(msg)

    def lineReceived(self, line):
        if self.promptDeferred is None:
            return
        d, self.promptDeferred = self.promptDeferred, None
        d.callback(line)



class SimpleIMAP4Client(imap4.IMAP4Client):
    """
    A client with callbacks for greeting messages from an IMAP server.
    """
    greetDeferred = None

    def serverGreeting(self, caps):
        print "Greeting"
        self.serverCapabilities = caps
        if self.greetDeferred is not None:
            d, self.greetDeferred = self.greetDeferred, None
            d.callback(self)



class SimpleIMAP4ClientFactory(protocol.ClientFactory):
    usedUp = False

    protocol = SimpleIMAP4Client


    def __init__(self, username, onConn):
        self.ctx = ssl.ClientContextFactory()

        self.username = username
        self.onConn = onConn


    def buildProtocol(self, addr):
        """
        Initiate the protocol instance. Since we are building a simple IMAP
        client, we don't bother checking what capabilities the server has. We
        just add all the authenticators twisted.mail has.  Note: Gmail no
        longer uses any of the methods below, it's been using XOAUTH since
        2010.
        """
        assert not self.usedUp
        self.usedUp = True

        p = self.protocol(self.ctx)
        p.factory = self
        p.greetDeferred = self.onConn

        p.registerAuthenticator(imap4.PLAINAuthenticator(self.username))
        p.registerAuthenticator(imap4.LOGINAuthenticator(self.username))
        p.registerAuthenticator(
                imap4.CramMD5ClientAuthenticator(self.username))

        return p


    def clientConnectionFailed(self, connector, reason):
        d, self.onConn = self.onConn, None
        d.errback(reason)



def cbServerGreeting(proto, username, password):
    """
    Initial callback - invoked after the server sends us its greet message.
    """
    # Hook up stdio
    tp = TrivialPrompter()
    stdio.StandardIO(tp)

    # And make it easily accessible
    proto.prompt = tp.prompt
    proto.display = tp.display

    # Try to authenticate securely
    return proto.authenticate(password
        ).addCallback(cbAuthentication, proto
        ).addErrback(ebAuthentication, proto, username, password
        )


def ebConnection(reason):
    """
    Fallback error-handler. If anything goes wrong, log it and quit.
    """
    log.err(reason)
    return reason


def cbAuthentication(result, proto):
    """
    Callback after authentication has succeeded.

    Lists a bunch of mailboxes.
    """
    return proto.list("", "*"
        ).addCallback(cbMailboxList, proto
        )


def ebAuthentication(failure, proto, username, password):
    """
    Errback invoked when authentication fails.

    If it failed because no SASL mechanisms match, offer the user the choice
    of logging in insecurely.

    If you are trying to connect to your Gmail account, you will be here!
    """
    failure.trap(imap4.NoSupportedAuthentication)
    return proto.prompt(
        "No secure authentication available. Login insecurely? (y/N) "
        ).addCallback(cbInsecureLogin, proto, username, password
        )


def cbInsecureLogin(result, proto, username, password):
    """
    Callback for "insecure-login" prompt.
    """
    if result.lower() == "y":
        # If they said yes, do it.
        return proto.login(username, password
            ).addCallback(cbAuthentication, proto
            )
    return defer.fail(Exception("Login failed for security reasons."))


def cbMailboxList(result, proto):
    """
    Callback invoked when a list of mailboxes has been retrieved.
    """
    result = [e[2] for e in result]
    s = '\n'.join(['%d. %s' % (n + 1, m) for (n, m) in zip(range(len(result)), result)])
    if not s:
        return defer.fail(Exception("No mailboxes exist on server!"))
    return proto.prompt(s + "\nWhich mailbox? [1] "
        ).addCallback(cbPickMailbox, proto, result
        )


def cbPickMailbox(result, proto, mboxes):
    """
    When the user selects a mailbox, "examine" it.
    """
    mbox = mboxes[int(result or '1') - 1]
    return proto.examine(mbox
        ).addCallback(cbExamineMbox, proto
        )


def cbExamineMbox(result, proto):
    """
    Callback invoked when examine command completes.
    """
    return proto.fetchMessage('1:*',
        ).addCallback(cbFetch, proto
        )
    # return proto.fetchSpecific('1:*',
    #                            headerType='HEADER.FIELDS',
    #                            headerArgs=['SUBJECT'],
    #     ).addCallback(cbFetch, proto
    #     )


@defer.inlineCallbacks
def cbFetch(result, proto):
    """
    Finally, display headers.
    """
    if result:
        keys = result.keys()
        keys.sort()
        for k in keys:
            # proto.display('%s %s' % (k, result[k]))
            yield handle_report(result[k]['RFC822'], mailing_ids)
    else:
        print "Hey, an empty mailbox!"

    Db.disconnect()
    defer.returnValue(proto.logout())


def cbClose(result):
    """
    Close the connection when we finish everything.
    """
    from twisted.internet import reactor
    reactor.stop()


def main():
    hostname = imap_server ##raw_input('IMAP4 Server Hostname: ')
    port = 143 ##raw_input('IMAP4 Server Port (the default is 143, 993 uses SSL): ')
    username = imap_account  or raw_input('IMAP4 Username: ')
    password = imap_pwd or util.getPassword('IMAP4 Password: ')

    onConn = defer.Deferred(
        ).addCallback(cbServerGreeting, username, password
        ).addErrback(ebConnection
        ).addBoth(cbClose)

    factory = SimpleIMAP4ClientFactory(username, onConn)

    from twisted.internet import reactor
    if port == '993':
        reactor.connectSSL(hostname, int(port), factory, ssl.ClientContextFactory())
    else:
        if not port:
            port = 143
        reactor.connectTCP(hostname, int(port), factory)
    reactor.run()


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    main()
