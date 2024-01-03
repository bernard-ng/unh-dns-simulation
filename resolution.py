from enum import IntEnum

from dns import Network, Zone
from message import Message, MessageHeader, MessageQuestion, RRClass, RRType, Opcode


class ResolutionStrategy(IntEnum):
    ITERATIVE = 1
    RECURSIVE = 2


class Resolver:
    def __init__(self, zone: Zone, network: Network, strategy: ResolutionStrategy.ITERATIVE):
        self.zone = zone
        self.network = network
        self.strategy = strategy

    def resolve(self, name: str):
        message = Message(
            MessageHeader(qr=0, opcode=Opcode.QUERY),
            MessageQuestion(qname=name, qclass=RRClass.IN, qtype=RRType.A)
        )

        if self.strategy == ResolutionStrategy.ITERATIVE:
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

        elif self.strategy == ResolutionStrategy.RECURSIVE:
            print("> #Resolver : Recursive resolution")
            try:
                message.header.ra = 1
                message.header.rd = 1

                root = self.network.get_random_root()
                answer = root.resolve(message)
                print(str(answer))

                rr = answer.answers[0]
                return rr.rdata
            except Exception:
                return None
        else:
            raise Exception(f"The resolution's strategy {self.strategy} is not supported")
