import socket
import sys
import select
import utils


class Client(object):

    def __init__(self, name, address, port):
        self.address = address
        self.port = int(port)
        self.name = name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.address, self.port))
            self.socket.send(pad(self.name))
        except:
            print utils.CLIENT_CANNOT_CONNECT.format(self.address, self.port)
            sys.exit()
        sys.stdout.write(utils.CLIENT_MESSAGE_PREFIX)
        sys.stdout.flush()

        self.start()

    def start(self):
        buffer = ''
        while True:

            ready_to_read, ready_to_write, in_error = select.select([sys.stdin, self.socket], [], [])

            for sock in ready_to_read:
                if sock == self.socket:
                    data = sock.recv(200)
                    buffer += data
                    if len(data) == 0:
                        print utils.CLIENT_SERVER_DISCONNECTED.format(self.address, self.port)
                        sys.exit()
                    if len(buffer) == 200:
                        msg = buffer.strip(' ')
                        buffer = ''
                        sys.stdout.write(utils.CLIENT_WIPE_ME)
                        sys.stdout.write('\r' + msg )
                        sys.stdout.write(utils.CLIENT_MESSAGE_PREFIX)
                        sys.stdout.flush()
                else:
                    msg = sys.stdin.readline()
                    if msg != '\n':
                        self.socket.send(pad(msg))
                    sys.stdout.write(utils.CLIENT_MESSAGE_PREFIX)
                    sys.stdout.flush()


def pad(msg):
    if msg[len(msg) - 1] == '\n':
        msg = msg[:len(msg) - 1]
    if len(msg) < 200:
        return msg.ljust(200)


args = sys.argv
if len(args) != 4:
    print "Please supply a name, server address, and port."
    sys.exit()
client = Client(args[1], args[2], args[3])