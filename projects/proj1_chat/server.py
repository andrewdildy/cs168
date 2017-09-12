import socket
import select
import sys
import utils

args = sys.argv


class Server(object):
    def __init__(self, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', int(port)))
        self.socket.listen(5)
        self.sockets = {self.socket: ServerSocket(self.socket, name='server')}
        self.channels = []

    def start(self):
        while True:

            ready_to_read, ready_to_write, in_error = select.select(self.sockets.keys(), [], [], 0)

            for sock in ready_to_read:
                if sock == self.socket:
                    sockfd, addr = self.socket.accept()
                    self.sockets[sockfd] = ServerSocket(sockfd)
                else:
                    try:
                        data = sock.recv(utils.MESSAGE_LENGTH)
                        s = self.sockets[sock]
                        s.add_to_buffer(data)
                        if s.buffer_full():
                            msg = s.buffer.rstrip(' ')
                            s.clear_buffer()
                            if self.sockets[sock].name is None:
                                self.sockets[sock].name = msg
                            else:
                                if msg[0] == '/':
                                    if msg[1:5] == 'join':
                                        self.join_channel(sock, msg[6:])
                                    elif msg[1:7] == 'create':
                                        self.create_channel(sock, msg[8:])
                                    elif msg[1:5] == 'list' and len(msg) == 5:
                                        if len(self.channels) > 0:
                                            sock.send(pad(', '.join(self.channels)))
                                    else:
                                        sock.send(pad(utils.SERVER_INVALID_CONTROL_MESSAGE.format(msg)))
                                else:
                                    if self.sockets[sock].channel is not None:
                                        self.broadcast(sock, '[' + self.sockets[sock].name + '] ' + msg, self.sockets[sock].channel)
                                    else:
                                        sock.send(pad(utils.SERVER_CLIENT_NOT_IN_CHANNEL))
                        elif len(data) == 0:
                            self.leave_channel(sock)
                            self.sockets.pop(sock)
                    except:
                        self.leave_channel(sock)
                        self.sockets.pop(sock)
                        continue

        self.socket.close()

    def broadcast(self, sock, msg, channel):
        for s, d in self.sockets.iteritems():
            if s != self.socket and s != sock and self.sockets[s].channel == channel and self.sockets[s].channel is not None:
                try:
                    s.send(pad(msg))
                except:
                    s.close()
                    if s in self.sockets:
                        self.sockets.pop(s)

    def join_channel(self, sock, channel):
        if channel:
            if channel in self.channels:
                self.leave_channel(sock)
                self.sockets[sock].channel = channel
                self.broadcast(sock, utils.SERVER_CLIENT_JOINED_CHANNEL.format(self.sockets[sock].name), channel)
            else:
                sock.send(pad(utils.SERVER_NO_CHANNEL_EXISTS.format(channel)))
        else:
            sock.send(pad(utils.SERVER_JOIN_REQUIRES_ARGUMENT))

    def create_channel(self, sock, channel):
        if channel:
            if channel not in self.channels:
                self.channels.append(channel)
                self.join_channel(sock, channel)
            else:
                sock.send(pad(utils.SERVER_CHANNEL_EXISTS.format(channel)))
        else:
            sock.send(pad(utils.SERVER_CREATE_REQUIRES_ARGUMENT))

    def leave_channel(self, sock):
        last_channel = self.sockets[sock].channel
        if last_channel is not None:
            self.broadcast(sock, utils.SERVER_CLIENT_LEFT_CHANNEL.format(self.sockets[sock].name), last_channel)


class ServerSocket(object):

    def __init__(self, sock, name=None, channel=None):
        self.socket = sock
        self.name = name
        self.channel = channel
        self.buffer = ''

    def clear_buffer(self):
        self.buffer = ''

    def buffer_full(self):
        return len(self.buffer) >= 200

    def add_to_buffer(self, data):
        self.buffer += data


def pad(msg):
    if msg[len(msg) - 1] != '\n':
        msg += '\n'
    if len(msg) < 200:
        return msg.ljust(200)

if len(args) != 2:
    print "Please supply a port."
    sys.exit()
server = Server(args[1])
server.start()
