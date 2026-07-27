# Attended one-time x402 payments to index the 4 TIME endpoints in the CDP Bazaar.
# One key-paste, one settle per endpoint (POST variants that carry the bazaar
# discovery declaration). Total ~0.10 USDC, all to your own treasury wallet.
#
# Run it yourself:
#   python pay_and_index_time.py
#
# Needs ~0.10 USDC on Base in the payer wallet. Real cost = a few cents of compute
# (/summary and /ask call Claude Haiku); the USDC just moves to your treasury.

import sys
import re
import json

from eth_account import Account
from x402 import x402ClientSync
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.http.clients.requests import x402_requests

BASE = "https://time.24klabs.ai"

# (path, approx_price_usd, request_body)
SERVICES = [
    ("/time",     0.001, {"tz": "UTC"}),
    ("/timezone", 0.001, {"tz": "UTC"}),
    ("/summary",  0.05,  {"tz": "UTC"}),
    ("/ask",      0.05,  {"question": "How many days until the winter solstice?"}),
]

total = sum(p for _, p, _ in SERVICES)

print("=" * 60)
print("24K Labs Time Lord -- index the 4 time endpoints in the CDP Bazaar")
print("Endpoints: %d   Approx total: ~$%.3f USDC (to your own treasury)" % (len(SERVICES), total))
print("=" * 60)
print()
print("Paste the PRIVATE KEY of the wallet you want to pay FROM (64 hex chars).")
print("It needs ~$%.2f USDC on Base. Use your small/burner wallet." % total)
print()

raw = input("Wallet to pay from (private key): ")
key = raw.strip().strip('"').strip("'").replace(" ", "")
hexpart = key[2:] if key.lower().startswith("0x") else key
if not key or not re.fullmatch(r"[0-9a-fA-F]+", hexpart or ""):
    print("Not a valid hex private key. Aborting -- nothing charged."); sys.exit(1)
if len(hexpart) == 40:
    print("That is a 40-char ADDRESS, not the 64-char private key. Aborting."); sys.exit(1)
if len(hexpart) != 64:
    print("A private key is 64 hex chars; you pasted %d. Aborting." % len(hexpart)); sys.exit(1)
try:
    acct = Account.from_key("0x" + hexpart)
except Exception as e:
    print("Did not parse (%s). Aborting." % type(e).__name__); sys.exit(1)

print()
print("Paying from wallet: %s" % acct.address)
print("Ctrl+C now to bail. Otherwise it settles %d payments (~$%.3f)." % (len(SERVICES), total))
print()

client = x402ClientSync()
client.register("eip155:8453", ExactEvmScheme(signer=acct))
session = x402_requests(client)

settled, failed = [], []
for path, price, body in SERVICES:
    url = BASE + path
    print("-> POST %-12s ($%.3f) ..." % (path, price), end=" ")
    try:
        r = session.post(url, json=body, timeout=120)
        if r.status_code == 200:
            print("SETTLED")
            settled.append(path)
        else:
            print("NOT 200 (%d): %s" % (r.status_code, r.text[:120]))
            failed.append(path)
    except Exception as e:
        print("ERROR %s: %s" % (type(e).__name__, str(e)[:120]))
        failed.append(path)

print()
print("=" * 60)
print("SETTLED (%d): %s" % (len(settled), ", ".join(settled) if settled else "none"))
if failed:
    print("FAILED  (%d): %s" % (len(failed), ", ".join(failed)))
print("=" * 60)
print(">>> Tell Nox which settled. He will re-scan the Bazaar for the time endpoints.")
