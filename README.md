# family-template

Start a new scraping family for the s1d-labs pool. A family is one kind of site (or one platform many sites share); the pool runs
its code on members' GitHub Actions minutes. This template is a complete, working family for
[books.toscrape.com](https://books.toscrape.com) (a public site made for scraping practice): copy it, then change it.

## Make your family

1. Ask the hub owner to **add the family** on [scrape.s1d.me/runners](https://scrape.s1d.me/runners) (name, what it scrapes, owner).
2. **Use this template** → owner **s1d-labs**, name = the family name, **Public** (public repos get free Actions minutes).
3. In your repo:
   - `scrape.json`: set `"family"` to the family name; list your tasks (one command each) and setup steps.
   - `family.py`: your projects (one queue of work per site), their target hosts, the env your command needs, the queue items,
     and the health checks.
   - `crawl.py` (or whatever your tasks run): the scraper.
4. Run the **setup** workflow (Actions → setup → Run workflow). It registers the projects, puts them in the pool and registers
   the health checks.
5. The hub starts runs in members' accounts when the pool is on and there is work. Watch it on scrape.s1d.me.

## What your code gets

The pool worker ([s1d-labs/runner](https://github.com/s1d-labs/runner)) checks out this repo at `main`, runs the `setup` steps from
`scrape.json`, and for each assignment runs the task's command here with:

| Variable | What |
|---|---|
| `SCRAPE_POOL_PROJECT` | the project to work on |
| `SCRAPE_JOB_INDEX`, `SCRAPE_TOTAL_JOBS` | this worker's slice |
| `SCRAPE_MAX_HOURS` | how long the command may run |
| `SCRAPE_HUB_URL` | the hub |
| your project's `env` | e.g. `SITE` |

Use `scrape_hub_client` (`HubClient`) to claim queue items, store records, upload files and report counters. Exit when there is
nothing left; the worker then asks the hub for the next assignment.

## Rules

- **Be polite.** Use `hub.settings["threads"]` and `delay_ms`, idle while `hub.settings["paused"]`, and report `n_http` and
  `t_http_s` for every request and `http_<code>` / `http_error` for failures: the hub throttles you from these.
- **Files go through the hub** (`hub.upload_many`): it signs each upload into the family's bucket (500 GB per member) and stops at
  the cap. Never put storage keys in this repo.
- **Public data only**; read the site's terms first. See the team docs on home.s1d.me (Scraping rules).
