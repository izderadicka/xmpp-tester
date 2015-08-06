#! /usr/bin/env python
'''
Created on Jul 14, 2015

@author: ivan
'''

import sys
import logging
import getpass
from argparse import ArgumentParser
from threading import Event
import sleekxmpp, sleekxmpp.xmlstream
from commander import Commander,Command
from copy import deepcopy

logger=logging.getLogger()

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
    
def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if  (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class ChatClient(sleekxmpp.ClientXMPP):
    # required plugins -   plugin name,  frienly name (will be atribute of this class instance,  config
    PLUGINS=[('xep_0030', 'disco', {}), # Service Discovery],
             ('xep_0085', 'chat_state', {}), # Chat State Notifications
             ('xep_0045', 'muc', {}), # Multiuser chat
             ('xep_0092', 'version', {})
             ]

    def __init__(self, jid, password, rooms, print_fn=None):
        super(ChatClient, self).__init__(jid, password)
        self.add_event_handler('session_start', self.start)
#         self.add_event_handler('message', self.message)
#         self.add_event_handler('changed_status', self.changed_status)
#         self.add_event_handler("groupchat_message", self.muc_message)
#         self.add_event_handler("roster_update", self.roster_update)
        for xep,_, pconfig in self.PLUGINS:
            self.register_plugin(xep, pconfig)
        self.ready=Event()
        self.rooms=rooms
        self.nick=jid.split('@')[0]
        self.jid=jid
        self.print_fn=print_fn
        
        self.add_filter('in', self.print_in,0)
        self.add_filter('out', self.print_out,0)
        
        
    def print_stanza(self,s, style=None):
        x=deepcopy(s.xml)
        indent(x)
        str_data = sleekxmpp.xmlstream.tostring(
                    x, xmlns=self.default_ns,
                    stream=self,top_level=True)
        
        self.p(str_data,style)
            
    def print_in(self,s):
        self.print_stanza(s, 'green')
        return s    
            
    def print_out(self,s):
        self.print_stanza(s, 'blue')
        return s
    
    
    def p(self, text, style=None):
        if self.print_fn:
            self.print_fn(text,style)
        else:
            print text
        
    def start(self, event):
        self.send_presence()
        self.get_roster(block=False)
        for xep,name,_ in self.PLUGINS:
            setattr(self, name, self.plugin[xep])
        for r in self.rooms or []:
            try:
                self.muc.joinMUC(r,
                                self.nick,
                                wait=False)
            except sleekxmpp.exceptions.XMPPError,e:
                logger.error('Chatroom Error : %s',e)
        self.ready.set()
        
    def wait_ready(self):
        self.ready.wait()
            
        
#     def message(self, msg):
#         if msg['type']=='groupchat':
#             return
#         elif msg['type']=='error':
#             logger.error('ERROR MSG: %s', msg)
#             return
#         logger.debug("MESSAGE: %s [%s] - %s", msg['from'], msg['type'], msg['body'])
#         
#     
#     def muc_message(self, msg):
#         logger.debug("%s::%s [%s] - %s" , msg['from'], msg['mucnick'], msg['type'], msg['body'])
#         
#     
#     def changed_status(self, prezence):
#         logger.debug( 'STATUS %s', prezence)
#         
#     def roster_update(self, roster):
#         logger.debug('ROSTER %s', roster)


class XMPPCommand(Command):
    def __init__(self, client):
        self.xc=client
        Command.__init__(self)
        
    def do_msg(self,*args):
        '''sends chat msg to address
1st param must be JID of recipient
Other params are joined as message body'''
        if len(args)<2:
            raise ValueError('Atleat two parameters are expected - recipient and message')
        xc.send_message(mto=args[0], mbody=' '.join(args[1:]), mtype='chat')

if __name__ == '__main__':
    p=ArgumentParser()
    p.add_argument('-d', '--debug', action='store_true', help='Debug logging')
    p.add_argument('-u', '--user', help="User ID (JID)", required=True)
    p.add_argument('-p', '--pwd', help='Password')
    p.add_argument('--ssl', action='store_true', help='Use SSL connection')
    p.add_argument('-s', '--server', help="server or server:port, if not present server from JID is used")
    p.add_argument('-r', '--room',  action='append', help='Chat room to join - can be used many times')
    args=p.parse_args()
    
    if not args.pwd:
        p=getpass.getpass('Password: ')
        args.pwd=p
        
    if args.server:
        s=args.server.split(':')
        s=map(lambda x: x.strip(),s)
        if len(s)>1:
            s[1]=int(s[1])
        args.server=s
    
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.ERROR,
                        format='%(levelname)-8s %(message)s')
    
    xc=ChatClient(args.user, args.pwd, args.room)
    c=Commander('XMPP Test Client', cmd_cb=XMPPCommand(xc))
    xc.print_fn=c.output
    
    if xc.connect(args.server or (), use_ssl=args.ssl):
        xc.process(block=False)
    else:
        print >>sys.stderr, 'Unable to connect'
        sys.exit(-1)
    xc.wait_ready(  )    
    c.loop()
    xc.disconnect()
    sys.exit(0)
    
    

    