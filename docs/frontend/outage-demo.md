# Outage demo (judges)

1. Look up an address once (fills `cache/`).
2. Reload with `?simulate_outage=nws,power` or set the page’s outage box.
3. Score should stay partial/honest with **data X hours old**, not invented numbers.

Every outbound feed uses 3 retries + 15s timeout (`tenacity`).