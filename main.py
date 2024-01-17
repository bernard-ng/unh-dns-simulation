import sys, os
import random
import re
import timeit

import requests
from faker import Faker
from tld import get_tld
from tqdm import tqdm
import pandas as pd
import matplotlib.pyplot as plt

from dns import Zone, Network
from message import RR, RRType, RRClass
from resolution import Resolver, ResolutionStrategy


def generate_hosts_records(base_zone: Zone) -> list[RR]:
    fake = Faker()

    domains = set()
    hosts_records: list[RR] = []

    with tqdm(total=10000, desc="Generating Domains") as pbar:
        while len(hosts_records) < 200:
            root_domain = fake.domain_name(levels=1)
            if root_domain not in domains:
                domains.add(root_domain)
                hosts_records.append(RR(root_domain, RRType.A, RRClass.IN, 3600, fake.ipv4_public(address_class='a')))

            pbar.update(1)

    authoritatives_a_records = [
        RR(f'ns{i}.auth-server.net', RRType.A, RRClass.IN, 3600, fake.ipv4_public(address_class='a')) for i in
        range(1, 11)
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
    resolver = Resolver(zone, network)

    option = input("Options (\n1. resolve a domain, \n2. compare strategies, \n3. see available domains): ")

    if option == '1':
        domain = input("Enter a domain to resolve : ")
        strategy = int(input("Strategy (1. Iterative, 2. Recursive): "))
        resolver.resolve(domain, strategy, True)

    elif option == '2':
        domain = input("Enter a domain to resolve : ")
        strategies = [ResolutionStrategy.ITERATIVE, ResolutionStrategy.RECURSIVE]
        results = {'strategy': [], 'iteration': [], 'time_taken': []}
        for strategy in strategies:
            for iteration in range(1, 1001):
                try:
                    time_taken = timeit.timeit(lambda: resolver.resolve(domain, strategy, False), number=1)
                    results['strategy'].append(strategy)
                    results['time_taken'].append(time_taken)
                    results['iteration'].append(iteration)
                except Exception:
                    pass

        # Create a DataFrame
        df = pd.DataFrame(results)
        df.to_csv(f'./data/resolution_times_{domain}.csv', index=False)

        sys.stdout = sys.__stdout__
        avg_times = df.groupby('strategy')['time_taken'].mean()
        print(avg_times)

        plt.figure(figsize=(10, 6))
        for strategy in strategies:
            strategy_df = df[df['strategy'] == strategy]
            plt.plot(strategy_df['iteration'], strategy_df['time_taken'], label=str(strategy))

        plt.title('DNS Resolution Time Distribution')
        plt.xlabel('Iteration')
        plt.ylabel('Time taken (seconds)')
        plt.legend()
        plt.show()

    elif option == '3':
        counter = 0
        for record in zone.records:
            if record.rtype == 'A':
                print(record.name)
                counter += 1
                if counter == 100:
                    break

