"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True # Set to True on an instance to disable its logging
    # POISON_MODE = True # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.start_timer()  # Starts calling handle_timer() at correct rate

        self.table = {}  # Entity -> NetworkNode
        self.connection_latencies = {}  # port -> latency
        self.connection_entities = {} # Entity -> port
    class NetworkNode:
        def __init__(self, latency, predecessor, port):
            self.latency = latency
            self.predecessor = predecessor
            self.predecessor_port = port
            self.timeout = 0

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.connection_latencies[port] = latency
        for entity, node in self.table.iteritems():
            for port in self.connection_latencies.keys():
                self.send(basics.RoutePacket(entity, node.latency), port=port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        if port in self.connection_latencies:
            if self.POISON_MODE:
                self.connection_latencies[port] = INFINITY
            else:
                del self.connection_latencies[port]
            to_delete = []
            for entity, node in self.table.iteritems():
                if node.predecessor_port == port:
                    if entity in self.connection_entities:
                        new_port = self.connection_entities[entity]
                        latency = self.connection_latencies[new_port]
                        self.table[entity] = self.NetworkNode(latency, entity, new_port)
                        continue
                    to_delete.append(entity)
            if to_delete:
                for entity in to_delete:
                    if self.POISON_MODE:
                        self.table[entity].latency = INFINITY
                    else:
                        del self.table[entity]


    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        if isinstance(packet, basics.RoutePacket):
            self.handle_route_packet(packet, port)
        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.handle_discovery_packet(packet, port)
        else:
            self.handle_other_packet(packet, port)

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        expired = []
        for entity, node in self.table.iteritems():
            if entity in self.connection_entities:
                new_port = self.connection_entities[entity]
                if new_port in self.connection_latencies:
                    new_latency = self.connection_latencies[new_port]
                    if new_latency < node.latency:
                        self.table[entity] = self.NetworkNode(new_latency, entity, new_port)
            node.timeout += self.DEFAULT_TIMER_INTERVAL
            if node.predecessor_port in self.connection_latencies:
                if node.timeout <= self.ROUTE_TIMEOUT and node.latency < INFINITY and self.connection_latencies[node.predecessor_port] < INFINITY:
                    for port in self.connection_latencies.keys():
                        self.send(basics.RoutePacket(entity, node.latency), port=port)
                    continue
            if self.POISON_MODE:
                for port in self.connection_latencies.keys():
                    self.send(basics.RoutePacket(entity, INFINITY), port=port)
            expired.append(entity)
        for entity in expired:
            del self.table[entity]

    def handle_route_packet(self, packet, port):
        if packet.src not in self.connection_entities:
            self.connection_entities[packet.src] = port
        if packet.latency >= INFINITY and self.table[packet.destination].predecessor_port == port:
            self.table[packet.destination] = self.NetworkNode(INFINITY, packet.src, port)
        if packet.destination in self.table:
            self.table[packet.destination].timeout = 0
            if self.table[packet.destination].latency >= INFINITY and self.POISON_MODE:
                return
        if port in self.connection_latencies:
            update = packet.latency + self.connection_latencies[port]
            if update < INFINITY:
                if packet.destination not in self.table or update <= self.table[packet.destination].latency or self.table[packet.destination].predecessor_port == port:
                    self.table[packet.destination] = self.NetworkNode(update, packet.src, port)

    def handle_discovery_packet(self, packet, port):
        if packet.src not in self.connection_entities:
            self.connection_entities[packet.src] = port
        self.table[packet.src] = self.NetworkNode(self.connection_latencies[port], packet.src, port)
        for p in self.connection_latencies.keys():
            if p != port:
                self.send(basics.RoutePacket(packet.src, self.table[packet.src].latency), port=p)

    def handle_other_packet(self, packet, port):
        if packet.dst in self.table:
            forward_port = self.table[packet.dst].predecessor_port
            if port != forward_port:
                self.send(packet, port=forward_port, flood=False)
