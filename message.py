import random
from enum import IntEnum, Enum

from tabulate import tabulate


class Opcode(IntEnum):
    QUERY = 0
    IQUERY = 1
    STATUS = 2


class Rcode(IntEnum):
    NO_ERROR = 0
    FORMAT_ERROR = 1
    SERVER_FAILURE = 2
    NAME_ERROR = 3
    NOT_IMPLEMENTED = 4
    REFUSED = 5


class RRClass(str, Enum):
    IN = "IN"  # the Internet system
    CH = "CH"  # the Chaos system


class RRType(str, Enum):
    A = "A"
    NS = "NS"


class RR:
    def __init__(self, name: str, rtype: RRType, rclass: RRClass, ttl: int, rdata: str):
        self.name = name
        self.rtype = rtype
        self.rclass = rclass
        self.ttl = ttl
        self.rdlength = len(rdata)
        self.rdata = rdata

    def __str__(self):
        return f"{self.name}\t\t\t{self.rtype}\t{self.rclass}\t{self.ttl}\t{self.rdata}"


class MessageHeader:
    def __init__(
        self,
        qr: int = 0,
        aa: int = 0,
        tc: int = 0,
        rd: int = 0,
        ra: int = 0,
        rcode: Rcode = Rcode.NO_ERROR,
        opcode: Opcode = Opcode.QUERY,
        z: int = 0,
        qdcount: int = 0,
        ancount: int = 0,
        nscount: int = 0,
        arcount: int = 0
    ):
        self.id = random.randint(0, 65535)
        self.qr = qr
        self.opcode = opcode
        self.aa = aa
        self.tc = tc
        self.rd = rd
        self.ra = ra
        self.z = z
        self.rcode = rcode
        self.qdcount = qdcount
        self.ancount = ancount
        self.nscount = nscount
        self.arcount = arcount

    def __str__(self):
        table = [
            [f'ID={self.id}'],
            [f'QR={self.qr}, OPCODE={self.opcode}, AA={self.aa}, TC={self.tc}, RD={self.rd}, RA={self.ra}, Z={self.z}, RCODE={self.rcode}'],
            [f'QDCOUNT={self.qdcount}'],
            [f'ANCOUNT={self.ancount}'],
            [f'NSCOUNT={self.nscount}'],
            [f'ARCOUNT={self.arcount}']
        ]
        return tabulate(table, tablefmt="grid")


class MessageQuestion:
    def __init__(self, qname: str, qtype: str = RRType.A, qclass: str = RRClass.IN):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass

    def __str__(self):
        return f"QNAME={self.qname}, QTYPE={self.qtype}, QCLASS={self.qclass}"


class Message:
    def __init__(
        self,
        header: MessageHeader,
        question: MessageQuestion,
        answers: list[RR] = None,
        authorities: list[RR] = None,
        additional: list[RR] = None
    ):
        self.header = header
        self.question = question

        # Optional sections in the DNS message
        self.answers = answers if answers else []
        self.authorities = authorities if authorities else []
        self.additional = additional if additional else []

    def __str__(self):
        table = [
            ["Header", self.header],
            ["Question", self.question],
            ["Answers", "\n".join(map(str, self.answers))],
            ["Authorities", "\n".join(map(str, self.authorities))],
            ["Additional", "\n".join(map(str, self.additional))]
        ]
        return tabulate(table, tablefmt="grid")

