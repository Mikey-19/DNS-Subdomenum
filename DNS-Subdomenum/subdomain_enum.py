import requests
import threading
import dns.resolver

# === SETTINGS ===
domain = 'youtube.com'
MAX_THREADS = 20
record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT']

# === GLOBAL VARIABLES ===
semaphore = threading.Semaphore(MAX_THREADS)
discovered_subdomains = []
lock = threading.Lock()

# === LOAD WORDLIST ===
with open('subdomains.txt') as file:
    subdomains = file.read().splitlines()

# === CHECK DNS RECORDS ===
def check_dns_records(full_domain):
    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(full_domain, rtype, lifetime=3)
            return True  # Subdomain exists
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.LifetimeTimeout, dns.resolver.NoNameservers):
            continue
    return False

# === MAIN SUBDOMAIN CHECK FUNCTION ===
def check_subdomain(subdomain):
    with semaphore:
        full_domain = f"{subdomain}.{domain}"

        if not check_dns_records(full_domain):
            return  # Skip if DNS resolution fails

        # Try HTTPS first, fallback to HTTP
        urls_to_try = [f"https://{full_domain}", f"http://{full_domain}"]
        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=3)
                if response.status_code < 400:
                    with lock:
                        if full_domain not in discovered_subdomains:
                            discovered_subdomains.append(full_domain)
                            print(f"[+] Discovered: {url}")
                    break
            except requests.RequestException:
                continue

# === MULTITHREADING ===
threads = []
for sub in subdomains:
    t = threading.Thread(target=check_subdomain, args=(sub,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

# === SAVE RESULTS ===
with open("discovered_subdomains.txt", 'w') as f:
    for sub in discovered_subdomains:
        print(sub, file=f)

print("\n✅ Scan complete! Results saved to 'discovered_subdomains.txt'")
