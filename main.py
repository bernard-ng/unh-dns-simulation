import os
import random
import re

import requests
from faker import Faker
from tld import get_tld
from tqdm import tqdm

from dns import Zone, Network
from message import RR, RRType, RRClass
from resolution import Resolver, ResolutionStrategy


def generate_hosts_records(base_zone: Zone) -> list[RR]:
    fake = Faker()

    domains = set()
    hosts_records: list[RR] = []

    with tqdm(total=10000, desc="Generating Domains") as pbar:
        while len(hosts_records) < 10000:
            root_domain = fake.domain_name(levels=1)
            if root_domain not in domains:
                domains.add(root_domain)

                hosts_records.append(RR(root_domain, RRType.A, RRClass.IN, 3600, fake.ipv4_public(address_class='a')))

            pbar.update(1)

    authoritatives_a_records = [
        RR(f'ns{i}.auth-server.net', RRType.A, RRClass.IN, 3600, fake.ipv4_public(address_class='a')) for i in range(1, 11)
    ]

    authoritatives_ns_records = []
    for i, host in enumerate(hosts_records):
        authoritative = random.choice(authoritatives_a_records)
        authoritatives_ns_records.append(RR(host.name, RRType.NS, RRClass.IN, 3600, authoritative.name))

    hosts_records.extend(authoritatives_ns_records)
    hosts_records.extend(authoritatives_a_records)
    return hosts_records


def get_record_from_zone(dns_root_zone: str, name: str, recursive=False) -> list[RR]:
    pattern = rf'^(({name})\s+(\d+)\s+(IN|CH)\s+(NS|A)\s+(.*))$'
    regex = re.compile(pattern, re.MULTILINE)
    matches = regex.findall(dns_root_zone)

    rrs = [RR(name=m[1], ttl=int(m[2]), rclass=m[3], rtype=m[4], rdata=m[5]) for m in matches]

    if recursive:
        for rr in rrs:
            rrs.extend(get_record_from_zone(dns_root_zone, rr.rdata))

    return rrs


def initialize_zone() -> Zone:
    print("> downloading root.zone file")
    dns_root_zone = requests.get("https://www.internic.net/domain/root.zone").text

    rrs = [get_record_from_zone(dns_root_zone, tld, True) for tld in ['.', 'com.', 'biz.', 'info.', 'net.', 'org.']]
    rrs = [r for rr in rrs for r in rr]  # flatten result

    print("> creating simulation root zone")
    root_zone = Zone(rrs)
    root_zone.merge(Zone(generate_hosts_records(root_zone)))
    root_zone.save_state('./data/root_zone.pickle')

    return root_zone


if __name__ == '__main__':
    if os.path.exists('./data/root_zone.pickle'):
        zone = Zone.load_state('./data/root_zone.pickle')
    else:
        zone = initialize_zone()

    network = Network()
    network.initialize_network(zone)

    resolver = Resolver(zone, network, ResolutionStrategy.ITERATIVE)
    resolver.resolve('klein.org')

