import dns.resolver

target_domain = 'femaid360.org'
record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']

resolver = dns.resolver.Resolver()
for record_types in record_types:
    try:
        answers = resolver.resolve(target_domain, record_types)
    except dns.resolver.NoAnswer:
        continue

    print(f"{record_types} records for {target_domain}:")
    for data in answers:
        print(f"  {data.to_text()}")
