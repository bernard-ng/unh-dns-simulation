import pickle
import random

from message import RRType, RR, Message, Rcode


class Zone:
    def __init__(self, records: list[RR] = None):
        self.records = records if records else []

    def __str__(self):
        return '\n'.join([str(rr) for rr in self.records])

    def add_record(self, rr: RR):
        self.records.append(rr)

    def search_record(self, name: str, rrtype: RRType = RRType.A, search_type: str = 'name') -> RR or None:
        for record in self.records:
            if (record.name == name or record.rdata == name) and record.rtype == rrtype:
                return record

        return None

    def save_state(self, filename: str) -> None:
        with open(filename, 'wb') as file:
            pickle.dump(self, file)

    def find_roots(self, rrtype=RRType.A) -> list[RR]:
        roots_ns = [record for record in self.records if record.name == '.']

        if rrtype == RRType.A:
            roots_a = []

            for root in roots_ns:
                rr = self.search_record(root.rdata, RRType.A)
                if rr:
                    roots_a.append(rr)
            return roots_a

        elif rrtype == RRType.NS:
            return roots_ns

    def find_tlds(self, name: str) -> list[RR]:
        return [record for record in self.records if record.name == f'{name}.']

    def find_authoritatives(self) -> list[RR]:
        return [record for record in self.records if record.name.find('auth-server.net') != -1]

    def merge(self, z) -> None:
        self.records.extend(z.records)

    @staticmethod
    def load_state(filename: str):
        with open(filename, 'rb') as file:
            return pickle.load(file)


class Server:
    def __init__(self, record: RR):
        self.zone = Zone()
        self.name = record.name
        self.ip = record.rdata
        self.__rr = record

    def to_record(self):
        return self.__rr

    def get_type(self):
        if isinstance(self, TLDServer):
            return 'tld'
        elif isinstance(self, RootServer):
            return 'root'
        elif isinstance(self, AuthoritativeServer):
            return 'authoritative'
        else:
            return 'host'

    def get_tld(self) -> str:
        return self.name.rstrip('.').split('.')[-1] + '.'


class TLDServer(Server):
    def resolve(self, message) -> Message:
        print(f"> #TLDServer : Resolving from {self.ip} ({self.name})")
        print(f"> #TLDServer : Looking for a Authoritative NS for {message.question.qname}")
        answer = self.zone.search_record(self.zone.search_record(message.question.qname, RRType.NS).rdata, RRType.A)

        message.header.qr = 1  # answering
        message.header.ancount += 1
        message.answers.append(answer)

        return message

    def recursive_resolve(self, message: Message, network) -> Message:
        print(f"> #TLDServer (R) : Resolving from {self.ip} ({self.name})")
        print(f"> #TLDServer (R) : Looking for a Authoritative NS for {message.question.qname}")
        answer = self.zone.search_record(self.zone.search_record(message.question.qname, RRType.NS).rdata, RRType.A)

        message.header.qr = 1  # answering
        message.header.ancount += 1
        message.answers.append(answer)

        print(f"> #TLDServer (R) : contacting the AuthoritativeServer")
        server = network.get_instance(message.answers[-1].rdata, 'authoritative')
        message.header.qr = 0
        response = server.resolve(message)

        return response


class AuthoritativeServer(Server):
    def resolve(self, message):
        print(f"> #AuthoritativeServer : Resolving from {self.ip} ({self.name})")
        answer = self.zone.search_record(message.question.qname, RRType.A)

        message.header.qr = 1
        message.header.aa = 1
        message.header.ancount += 1
        message.authorities.append(self.to_record())
        message.answers.append(answer)

        return message


class RootServer(Server):
    def find_tld(self, qname: str) -> RR:
        tlds_ns = []
        tld = qname.split('.')[-1] + '.'

        for record in self.zone.records:
            if record.name == tld and record.rtype == RRType.NS:
                tlds_ns.append(record)

        tlds_a = []
        for rr in tlds_ns:
            tlds_a.append(self.zone.search_record(rr.rdata, RRType.A))

        print(f"> #RootServer : Found {len(tlds_a)} ({tld}) TLDServers for {qname}")
        return random.choice(tlds_a)

    def resolve(self, message: Message) -> Message:
        print(f"> #RootServer : Resolving from {self.ip} ({self.name})")
        print(f"> #RootServer : Looking for a TLD NS for {message.question.qname}")
        answer = self.find_tld(message.question.qname)

        message.header.qr = 1  # answering
        message.header.ancount += 1
        message.answers.append(answer)

        return message

    def recursive_resolve(self, message: Message, network) -> Message:
        print(f"> #RootServer (R) : Resolving from {self.ip} ({self.name})")
        print(f"> #RootServer (R) : Looking for a TLD NS for {message.question.qname}")
        answer = self.find_tld(message.question.qname)

        message.header.qr = 1  # answering
        message.header.ancount += 1
        message.answers.append(answer)

        print(f"> #RootServer (R) : contacting the TLDServer")
        tld = network.get_instance(message.answers[-1].rdata, 'tld')
        message.header.qr = 0
        response = tld.recursive_resolve(message, network)

        return response


class Network:
    def __init__(self):
        self.root_servers: list[RootServer] = []
        self.tld_servers: list[TLDServer] = []
        self.authoritative_servers: list[AuthoritativeServer] = []

    def get_instance(self, address: str, server: str) -> Server or None:
        if server == 'root':
            for root in self.root_servers:
                if root.ip == address:
                    return root
        elif server == 'tld':
            for tld in self.tld_servers:
                if tld.ip == address:
                    return tld
        else:
            for server in self.authoritative_servers:
                if server.ip == address:
                    return server

    def get_random_root(self) -> RootServer:
        return random.choice(self.root_servers)

    def get_random_tld(self, records: list[RR]) -> TLDServer:
        ips = [record.rdata for record in records]
        servers = []
        for ip in ips:
            for server in self.tld_servers:
                if server.ip == ip:
                    servers.append(server)

        return random.choice(servers)

    def initialize_network(self, zone: Zone):
        self.root_servers = [RootServer(rr) for rr in zone.find_roots(RRType.A)]

        self.tld_servers = []
        for tld_name in ['com', 'org', 'info', 'net', 'biz']:
            for rr in zone.find_tlds(tld_name):
                self.tld_servers.append(TLDServer(zone.search_record(rr.rdata, RRType.A)))

        self.authoritative_servers = [AuthoritativeServer(rr) for rr in zone.find_authoritatives()]

        # making root server aware of tlds
        for root in self.root_servers:
            for tld_server in self.tld_servers:
                root.zone.add_record(tld_server.to_record())
                root.zone.add_record(zone.search_record(tld_server.to_record().name, RRType.NS))

        # making tlds server aware of authoritative servers
        for tld_server in self.tld_servers:
            rtld = zone.search_record(tld_server.name, RRType.NS)

            for authoritative_server in self.authoritative_servers:
                tld_server.zone.add_record(authoritative_server.to_record())

            for record in zone.records:
                if record.name.split('.')[-1] + '.' == rtld.name and record.rtype == RRType.NS:
                    tld_server.zone.add_record(record)

        # making authoritative server aware of hosts
        for authoritative in self.authoritative_servers:
            for record in zone.records:
                if record.rdata == authoritative.to_record().name and record.rtype == RRType.NS:
                    authoritative.zone.add_record(record)
                    authoritative.zone.add_record(zone.search_record(record.name, RRType.A))
