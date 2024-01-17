import sys, os
from enum import IntEnum

from dns import Network, Zone
from message import Message, MessageHeader, MessageQuestion, RRClass, RRType, Opcode


class ResolutionStrategy(IntEnum):
    ITERATIVE = 1
    RECURSIVE = 2


class Resolver:
    def __init__(self, zone: Zone, network: Network):
        self.zone = zone
        self.network = network

    def __iterative(self, message):
        print("> #Resolver : Iterative resolution")
        try:
            print("> #Resolver : contacting a random RootServer")
            root = self.network.get_random_root()
            response = root.resolve(message)

            print(f"> #Resolver : contacting the TLDServer")
            tld = self.network.get_instance(response.answers[-1].rdata, 'tld')
            message.header.qr = 0
            response = tld.resolve(message)

            print(f"> #Resolver : contacting the AuthoritativeServer")
            server = self.network.get_instance(response.answers[-1].rdata, 'authoritative')
            message.header.qr = 0
            response = server.resolve(message)

            print(f"{message.question.qname} resolved to {response.answers[-1].rdata}")
            print(message)
        except Exception as e:
            print(f"Unable to find the ip address for {message.question.qname}")
            print(e)

    def __recursive(self, message):
        print("> #Resolver : Recursive resolution")
        try:
            message.header.ra = 1
            message.header.rd = 1

            root = self.network.get_random_root()
            response = root.recursive_resolve(message, self.network)

            print(f"{message.question.qname} resolved to {response.answers[-1].rdata}")
            print(message)
        except Exception:
            return None

    def resolve(self, name: str, strategy: ResolutionStrategy.ITERATIVE, logger: bool = True):
        message = Message(
            MessageHeader(qr=0, opcode=Opcode.QUERY),
            MessageQuestion(qname=name, qclass=RRClass.IN, qtype=RRType.A)
        )

        if not logger:
            sys.stdout = open(os.devnull, 'w')

        if strategy == ResolutionStrategy.ITERATIVE:
            self.__iterative(message)

        elif strategy == ResolutionStrategy.RECURSIVE:
            self.__recursive(message)
        else:
            raise Exception(f"The resolution's strategy {strategy} is not supported")

        if not logger:
            sys.stdout = sys.__stdout__
