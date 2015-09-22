import enum
import json

import panda3d.core as p3d
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator


class MessageTypes(enum.IntEnum):
    update_entity = 1
    remove_entity = 2
    register_player = 3
    player_id = 4
    player_input = 5


class NetworkManager(object):
    def __init__(self, ecs, transport_layer, is_server=False):
        self.ecs = ecs
        self.netrole = 'SERVER' if is_server else 'CLIENT'
        self.transport = transport_layer(self.message_handler)
        self.next_netid = 1
        self.server_update_rate = 1/30
        self.server_update_accum = 0

    def register_entity(self, entity):
        if self.netrole == 'SERVER':
            entity.netid = self.next_netid
            self.next_netid += 1

    def update(self, dt):
        self.transport.update()

        if self.netrole == 'SERVER':
            self.server_update_accum += dt
            if self.server_update_accum >= self.server_update_rate:
                for entity in [i for i in self.ecs.entities if i.netid != 0]:
                    self.transport.broadcast(MessageTypes.update_entity, {
                        'netid': entity.netid,
                        'data': json.dumps(entity.serialize()),
                    })
                for netid in self.ecs.removed_entities:
                    self.transport.broadcast(MessageTypes.remove_entity, {
                        'netid': netid,
                    })

                self.server_update_accum = 0

    def message_handler(self, connection, msgid, data):
        if msgid == MessageTypes.update_entity:
            entities = [i for i in self.ecs.entities if i.netid == data['netid']]
            if len(entities) == 0:
                entity = self.ecs.create_entity()
                self.register_entity(entity)
            else:
                entity = entities[0]

            #print(message.data.value)
            entity.update(data['netid'], json.loads(data['data']))
        elif msgid == MessageTypes.remove_entity:
            entities = [i for i in self.ecs.entities if i.netid == data['netid']]
            if len(entities) > 0 and data['netid'] != 0:
                self.ecs.remove_entity(entities[0])
        else:
            base.game_mode.handle_net_message(connection, msgid, data)

    def broadcast(self, msgid, data):
        self.transport.broadcast(msgid, data)

    def send_to(self, connection, msgid, data):
        self.transport.send_to(connection, msgid, data)

    def start_server(self, port):
        self.transport.start_server(port)

    def start_client(self, host, port):
        self.transport.start_client(host, port)


class BaseTransportLayer(object):
    def __init__(self, message_handler):
        self.message_handler = message_handler

    def update(self):
        raise NotImplementedError()

    def broadcast(self, msgid, data):
        raise NotImplementedError()

    def send_to(self, connection, msgid, data):
        raise NotImplementedError()

    def start_server(self, port):
        raise NotImplementedError()

    def start_client(self, host, port):
        raise NotImplementedError()


class PandaTransportLayer(BaseTransportLayer):
    def __init__(self, message_handler):
        super().__init__(message_handler)

        self.manager = p3d.QueuedConnectionManager()
        self.listener = None
        self.reader = p3d.QueuedConnectionReader(self.manager, 0)
        self.writer = p3d.ConnectionWriter(self.manager, 0)
        self.connections = []

    def _parse_msg_hton(self, msgid, data):
        msg = PyDatagram()
        msg.add_uint8(msgid)

        if msgid == MessageTypes.update_entity:
            msg.add_uint32(data['netid'])
            msg.add_string(data['data'])
        elif msgid == MessageTypes.remove_entity:
            msg.add_uint32(data['netid'])
        elif msgid == MessageTypes.register_player:
            pass
        elif msgid == MessageTypes.player_id:
            msg.add_uint32(data['netid'])
        elif msgid == MessageTypes.player_input:
            msg.add_uint32(data['netid'])
            msg.add_int8(data['movement_x'])
            msg.add_string(data['action_set'])
        else:
            raise RuntimeError("Unknown msgid:", msgid)

        return msg

    def _parse_msg_ntoh(self, datagram):
        msg = PyDatagramIterator(datagram)
        msgid = msg.get_uint8()
        data = {}

        if msgid == MessageTypes.update_entity:
            data['netid'] = msg.get_uint32()
            data['data'] = msg.get_string()
        elif msgid == MessageTypes.remove_entity:
            data['netid'] = msg.get_uint32()
        elif msgid == MessageTypes.register_player:
            pass
        elif msgid == MessageTypes.player_id:
            data['netid'] = msg.get_uint32()
        elif msgid == MessageTypes.player_input:
            data['netid'] = msg.get_uint32()
            data['movement_x'] = msg.get_int8()
            data['action_set'] = msg.get_string()
        else:
            RuntimeError("Unknown msgid:", msgid)

        return msgid, data

    def update(self):
        # Check for new connections
        if self.listener and self.listener.new_connection_available():
            rendezvous = p3d.PointerToConnection()
            addr = p3d.NetAddress()
            new_conn = p3d.PointerToConnection()

            if self.listener.get_new_connection(rendezvous, addr, new_conn):
                new_conn = new_conn.p()
                print("New connection:", new_conn)
                self.connections.append(new_conn)
                self.reader.add_connection(new_conn)

        # Check for data
        while self.reader.data_available():
            datagram = p3d.NetDatagram()

            if self.reader.get_data(datagram):
                #print("New data:", datagram)
                self.message_handler(datagram.get_connection(), *self._parse_msg_ntoh(datagram))

    def broadcast(self, msgid, data):
        datagram = self._parse_msg_hton(msgid, data)
        for conn in self.connections:
           self.writer.send(datagram, conn)

    def send_to(self, connection, msgid, data):
        datagram = self._parse_msg_hton(msgid, data)
        self.writer.send(datagram, connection)

    def start_server(self, port):
        self.listener = p3d.QueuedConnectionListener(self.manager, 0)
        socket = self.manager.open_TCP_server_rendezvous(port, 100)
        self.listener.add_connection(socket)

        print("Server waiting for connections")

    def start_client(self, host, port):
        conn = self.manager.open_TCP_client_connection(host, port, 3000)

        if conn:
            print("Connected to server:", conn)
            self.connections.append(conn)
            self.reader.add_connection(conn)
        else:
            raise RuntimeError("Failed to connect to server")
