#!/usr/bin/env python

import argparse
import asyncore
import collections
import logging
import socket

DEFAULT_LOGGING_LEVEL = logging.DEBUG

MAX_MESSAGE_LENGTH = 1024

# Default host and port for TCP server/client connections
DEFAULT_WINDTUNNEL_BIND_HOST = '0.0.0.0'
DEFAULT_WINDTUNNEL_PORT = 12321

# Default port to listen for incoming UDP datagrams
DEFAULT_WIND_UDP_PORT = 5005

# Default port for clients to repeat the original UDP datagrams
DEFAULT_WIND_UDP_REPEATER_PORT = 11111


class RemoteClient(asyncore.dispatcher):
    def __init__(self, host, socket, addr, log):
        asyncore.dispatcher.__init__(self, socket)
        self.host = host
        self.outbox = collections.deque()
        self.addr = addr
        self.log = log

    def send_wind(self, wind_datagram):
        self.outbox.append(wind_datagram)

    def handle_read(self):
        client_message = self.recv(MAX_MESSAGE_LENGTH)
        if client_message:
            self.log.debug('received a message from client: %s', client_message)

    def handle_write(self):
        if not self.outbox:
            return
        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

    def handle_close(self):
        self.host.remove_client(self.addr)
        self.log.info('closing remote client to %s', self.addr)
        self.close()


class Host(asyncore.dispatcher):
    def __init__(self, addr):
        asyncore.dispatcher.__init__(self)
        self.log = logging.getLogger("windtunnel host [{}]".format(addr))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(addr)
        self.listen(1)
        self.remote_clients = {}

    def handle_accept(self):
        socket, addr = self.accept() # For the remote client.
        self.log.info('client connected from %s', addr)
        self.remote_clients[addr] = RemoteClient(self, socket, addr, self.log)

    def remove_client(self, addr):
        self.log.info('removing client %s from distribution list', addr)
        self.remote_clients.pop(addr, 'None')

    def receive_wind(self, wind_datagram):
        if self.remote_clients:
            self.log.debug('broadcasting wind datagram: %s', wind_datagram)
            for remote_addr, remote_client in self.remote_clients.items():
                self.log.debug("sending to: %s", remote_addr)
                remote_client.send_wind(wind_datagram)


class WindListener(asyncore.dispatcher):
    def __init__(self, addr):
        asyncore.dispatcher.__init__(self)
        self.log = logging.getLogger("windtunnel windlistener [{}]".format(addr))
        self.log.debug('Opening socket at %s', addr)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(addr)
        self.log.info('Listening at %s', addr)

    def handle_read(self):
        dgram = self.recv(MAX_MESSAGE_LENGTH)
        logging.debug("received: %s", dgram)

    def writable(self):
        return False # don't want write notifies


class ForwardingWindListener(WindListener):
    def __init__(self, addr, host):
        self.host=host
        WindListener.__init__(self, addr)

    def handle_read(self):
        dgram = self.recv(MAX_MESSAGE_LENGTH)
        logging.debug("received: %s", dgram)
        self.host.receive_wind(dgram)


class Client(asyncore.dispatcher):
    def __init__(self, addr, repeater_port, name=None):
        asyncore.dispatcher.__init__(self)
        if name:
            self.log = logging.getLogger("windtunnel client [{}]".format(name))
        else:
            self.log = logging.getLogger("windtunnel client [{}]".format(addr))
        self.log.debug('Connecting to host at %s', addr)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(addr)
        self.log.info('Connected to host at %s', addr)
        self.name = name
        self.repeater_port = repeater_port
        self.outbox = collections.deque()

    def handle_write(self):
        if not self.outbox:
            return
        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

    def handle_read(self):
        message = self.recv(MAX_MESSAGE_LENGTH)
        if message:
            self.log.debug('Received message: %s', message)
            self.log.debug('Repeating message to %s', self.repeater_port)
            repeater_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            repeater_sock.sendto(message, ('127.0.0.1', self.repeater_port))
            repeater_sock.close()

    def handle_close(self):
        self.log.info('Connection closed by server')
        self.close()


def debug_mode(args):
    logging.info('Creating host')
    windtunnel_addr = ('localhost', DEFAULT_WINDTUNNEL_PORT)
    host = Host(windtunnel_addr)
    logging.info('Creating wind udp listener')
    wind_listener = ForwardingWindListener(DEFAULT_WIND_UDP_PORT, host)
    logging.info('Creating wind udp repeater listener')
    wind_repeat_listener = WindListener(DEFAULT_WIND_UDP_REPEATER_PORT)
    logging.info('Creating clients')
    alice = Client(windtunnel_addr, 'Alice')
    bob = Client(windtunnel_addr, 'Bob')
    logging.info('Looping')
    asyncore.loop()

def client_mode(args):
    logging.info('Starting client')
    client = Client((args.host, args.port), args.udp_repeater_port)
    asyncore.loop()

def server_mode(args):
    logging.info('Starting server')
    host = Host((args.tcp_server_bind_host, args.tcp_server_port))
    wind_listener = ForwardingWindListener((args.tcp_server_bind_host, args.udp_listen_port), host)
    asyncore.loop()

def udp_listener_mode(args):
    wind_repeat_listener = WindListener(('0.0.0.0', args.udp_listen_port))
    asyncore.loop()


if __name__ == '__main__':
    logging.basicConfig(level=DEFAULT_LOGGING_LEVEL)
    parser = argparse.ArgumentParser(prog='windtunnel.py')
    subparsers = parser.add_subparsers()
    parser_client = subparsers.add_parser('client', help='connect as a windtunnel client')
    parser_client.add_argument(
        'host',
        help='host of windtunnel server to connect to')
    parser_client.add_argument(
        '--port',
        '-p',
        type=int,
        default=DEFAULT_WINDTUNNEL_PORT,
        help="port of windtunnel server to connect to, default to {}".format(DEFAULT_WINDTUNNEL_PORT))
    parser_client.add_argument(
        '--udp_repeater_port',
        '-u',
        type=int,
        default=DEFAULT_WIND_UDP_REPEATER_PORT,
        help="port to send repeated UDP datagrams to, default to {}".format(DEFAULT_WIND_UDP_REPEATER_PORT))
    parser_client.set_defaults(func=client_mode)
    parser_server = subparsers.add_parser('server', help='start a windtunnel client')
    parser_server.add_argument(
        '--tcp_server_bind_host',
        '-s',
        default=DEFAULT_WINDTUNNEL_BIND_HOST,
        help="host to bind server to, default to {}".format(DEFAULT_WINDTUNNEL_BIND_HOST))
    parser_server.add_argument(
        '--tcp_server_port',
        '-t',
        type=int,
        default=DEFAULT_WINDTUNNEL_PORT,
        help="port to accept TCP connections from clients on, default to {}".format(DEFAULT_WINDTUNNEL_PORT))
    parser_server.add_argument(
        '--udp_listen_port',
        '-u',
        type=int,
        default=DEFAULT_WIND_UDP_PORT,
        help="port on which to listen for wind UDP datagrams, default to {}".format(DEFAULT_WIND_UDP_PORT))
    parser_server.set_defaults(func=server_mode)
    parser_udp_listener = subparsers.add_parser('udp_listener', help='start in udp listener mode')
    parser_udp_listener.add_argument(
        '--udp_listen_port',
        '-u',
        type=int,
        default=DEFAULT_WIND_UDP_REPEATER_PORT,
        help="port on which to listen for wind UDP datagrams, default to {}".format(DEFAULT_WIND_UDP_REPEATER_PORT))
    parser_udp_listener.set_defaults(func=udp_listener_mode)
    parser_debug = subparsers.add_parser('debug', help='start in debug mode')
    parser_debug.set_defaults(func=debug_mode)
    args = parser.parse_args()
    args.func(args)
