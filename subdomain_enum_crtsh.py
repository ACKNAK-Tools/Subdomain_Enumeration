#!/usr/bin/env python3

# inf0junki3, 2016.
# Extracts subdomains using crt.sh(searching through Certificate Transparency logs)
# Prerequisites: python3, feedparser, requests
# pip3 install feedparser

import dns.resolver
import feedparser
import requests
import sys
import argparse
import subprocess
from shlex import quote

base_url = "https://crt.sh/atom?q=%25.{}"

def get_rss_for_domain(domain):
    """Pull the domain identity information from crt.sh"""
    results_raw = requests.get(base_url.format(domain)).content
    results_entries = feedparser.parse(results_raw)["entries"]
    return results_entries

def parse_entries(identity, results_list):
    """This is pretty gross, but necessary when using crt.sh: parse the contents of the summary
    entry and return individual host names."""
    line_breaks = ["<br>", "<br />"]
    for cur_break in line_breaks:
        if cur_break in identity["summary"]:
            entries_raw = identity["summary"][:identity["summary"].index(cur_break)].replace("&nbsp;", "\n")
    entries     = entries_raw.split("\n")
    for entry in entries:
        trimmed_entry       = entry.strip()
        stringified_entry   = str(trimmed_entry)
        results_list.append(stringified_entry)

def format_entries(results, do_resolve_dns):
    """Sort and deduplicate hostnames and, if DNS resolution is turned on, resolve hostname"""
    sorted_results = sorted(set(results))
    if do_resolve_dns:
        final_results = []
        for cur_result in sorted_results:
            if "*" not in cur_result:
                try:
                    ip_addresses = dns.resolver.query(cur_result)
                    for ip_address in ip_addresses:
                        final_results.append("{}\t{}".format(cur_result, ip_address))
                except dns.resolver.NoAnswer:
                    final_results.append(cur_result)
            else:
                final_results.append(cur_result)
    else:
        final_results = sorted_results
    return final_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Pull a list of CT entries for a set of domains")
    parser.add_argument("--domains",
                        metavar = "D",
                        nargs   = "+",
                        help    = "The domains you wish to search for")
    parser.add_argument("--resolve_dns",
                        action  = "store_true",
                        help    = "Perform a DNS lookup on the host name")
    args = parser.parse_args()
    domains = args.domains
    results = []
    if (domains == None):
        parser.print_help()
    else:
        for cur_domain in domains:
            domain = cur_domain.strip()
            results_entries = get_rss_for_domain(domain)
            for cur_entry in results_entries:
                parse_entries(cur_entry, results)
        final_results = format_entries(results, args.resolve_dns)
        print("Domains found without IP assigned might be internals")
        for elem in final_results:
            command = 'dig +noall +answer {}'.format(quote(elem))
            print("[+] %s" % elem)
            subprocess.run(command, shell=True)
