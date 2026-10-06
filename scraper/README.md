# Link recheck

PathForge keeps curation human-led:

1. A curator adds a resource to `catalog/resources.yaml` and fills in its level, cost and certificate details.
2. After personally checking them, the curator sets the `curator_checks` to `PASS`.
3. This script checks that the link still works and records the result.

A resource shows as **Verified** only when all four curator checks are `PASS` **and** the latest link check passed.

Each link check gets one of three results:

- `PASS`: the page loaded.
- `FAIL`: the page is really gone (for example a 404 to a normal GET request). The resource is hidden from learners until it is fixed.
- `BLOCKED`: the site refuses automated requests (401/403/429). The resource stays visible as "Review pending". Open the link yourself to confirm it.
- *Not reached*: no internet, a DNS failure (e.g. `getaddrinfo failed`) or a timeout. This says nothing about the link, so the result is **not saved**. Run the check again later.

A failed HEAD request is always retried with GET, because some sites answer HEAD with a false 404.

```bash
python -m scraper.recheck                   # check every resource
python -m scraper.recheck --pending-only    # only links that were never checked
python -m scraper.recheck --retry-failed    # only links that failed last time
python -m scraper.recheck --path web_dev    # one path
python -m scraper.recheck --limit 3 --dry-run
```

Results are stored in the `url_checks` table, keyed by the resource `id`, so running `python seed.py` again does not erase them.

The script deliberately does **not** search the web for new resources or judge quality automatically — those decisions stay with a human.
