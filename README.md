# Click613 Yahrzeit Calendar

A calendar of **Gedolim yahrzeits** and **Jewish history of the day**, by Hebrew date, that runs on GitHub by itself.
Every morning GitHub rebuilds it and publishes it to GitHub Pages: a website people can browse, plus data files
that any website, screen or app (for example the KBY live screen / thelakewoodluach.com) can read whenever it wants.

- Owner: Click613 (GitHub account under admin@click613.com). Chanoch Rosenthal can be added as a collaborator.
- Live site: `https://<OWNER>.github.io/click613-yahrzeit-calendar/` (replace `<OWNER>` with the GitHub username once the repo exists).
- Data: about 1,590 confirmed yahrzeits on 351 Hebrew dates and about 600 history events. Every name is checked against two or more independent sources.

## What is in this repo

```
data/
  yahrzeits.json     confirmed yahrzeits (2+ sources each), keyed by Hebrew date  <- edit this
  history.json       Jewish history events (2+ sources each), keyed by Hebrew date <- edit this
  unconfirmed.json   single-source or conflicting names. NOT shown on the calendar or in the API lists
scripts/
  build.py           builds site/ (website + API) from data/. Only needs pyluach
  add_yahrzeit.py    helper to add one name from the command line
web/                 the website (index.html, assets/app.js, assets/style.css, logo)
.github/workflows/
  daily.yml          daily build + deploy to GitHub Pages, manual "Run workflow" button, failure alert
  check.yml          checks every pull request (data valid, site builds)
requirements.txt     pyluach (Hebrew calendar)
```

`site/` is generated and is not committed.

## The data format

Keys are Hebrew dates written `<day>-<Month>`: `18-Cheshvan`, `7-Adar`, `14-Adar-II`.
Months: `Tishrei Cheshvan Kislev Teves Shevat Adar Adar-I Adar-II Nisan Iyar Sivan Tammuz Av Elul`.

```json
"18-Cheshvan": [
  {
    "name_he": "רבי נחום פרצוביץ",
    "name_en": "R' Nachum Partzovitz",
    "father_he": "רבי אריה צבי פרצוביץ",
    "father_en": "R' Aryeh Tzvi Partzovitz",
    "year_heb": "5747",
    "year": "1986",
    "who": "Rosh Yeshivas Mir in Jerusalem",
    "sources": [
      {"name": "he.wikipedia date page י\"ח בחשוון", "url": "https://he.wikipedia.org/wiki/..."},
      {"name": "torahtots.com This Month in Jewish History: 18 Cheshvan", "url": "https://www.torahtots.com/timecapsule/thismonth/cheshvan.htm"}
    ]
  }
]
```

Optional fields: `adar` (`"I"` or `"II"`, only for Adar yahrzeits), `burial` (`{"en", "he", "map"}`), `notes`, `origin` (where the name came from; not published).

History events: `year_heb`, `year`, `en`, `he` (optional), `sources`.

**Adar and the 30th:** the calendar follows hebcal's yahrzeit rules. A yahrzeit stored under plain `Adar` is kept in **Adar I** in a leap year,
unless it is marked `"adar": "II"`. `30-Adar-I` falls on 30 Shevat in a plain year. A 30 Cheshvan / 30 Kislev yahrzeit moves to the 1st of the next month in a year that has no 30th
(or stays on the 29th if the first anniversary had no 30th).

## How to add or fix a yahrzeit (pull request)

The rule: **two independent sources for every name**. One source only? Put it in `data/unconfirmed.json` with a `why_unconfirmed` line.

On the GitHub website (no tools needed):
1. Open `data/yahrzeits.json`, click the pencil (Edit).
2. Find the date (Ctrl+F `"18-Cheshvan"`) and add an entry in the same shape as the ones around it. Mind the commas.
3. "Commit changes" -> choose **Create a new branch and start a pull request**. Write the two sources in the description.
4. The **Check pull request** workflow runs. Green = the data is valid and the site builds. Red = open the run to see the line it complains about.
5. Merge. The site and all feeds update within a few minutes (the daily workflow runs on every change to `data/`).

From a computer:
```bash
python scripts/add_yahrzeit.py --date 18-Cheshvan --name-en "R' ..." --name-he "רבי ..." \
   --father-en "R' ..." --year-heb 5747 --year 1986 --who "one line" \
   --source "first source" --source "https://second-source"
python scripts/build.py --check
git checkout -b add-yahrzeit && git commit -am "Add R' ... (18 Cheshvan)" && git push -u origin add-yahrzeit
```

To confirm an unconfirmed name: find a second source, move the entry from `unconfirmed.json` to `yahrzeits.json`, add the source, remove `why_unconfirmed`.

## API for Instinct and anyone else

All files are plain static JSON/CSV/ICS on GitHub Pages: no key, no login, CORS open. Base URL: `https://<OWNER>.github.io/click613-yahrzeit-calendar/`

| URL | What |
|---|---|
| `api/today.json` | today (New York date): Hebrew date, yahrzeits, history |
| `api/tomorrow.json` | tomorrow = the Hebrew date that begins tonight (use this for "a day in advance") |
| `api/day/2026-11-05.json` | any civil date, from a week back to about 14 months ahead |
| `api/date/18-Cheshvan.json` | one Hebrew date as stored (all years) |
| `api/all.json` | everything: yahrzeits + history by Hebrew date |
| `api/yahrzeits.json`, `api/history.json` | each list by Hebrew date |
| `api/yahrzeits.csv`, `api/history.csv` | the same for Excel / Google Sheets |
| `api/calendar.ics` | calendar feed: subscribe in Google / Apple / Outlook Calendar (one all-day event per day) |
| `api/month/Cheshvan.json` | one month (used by the website) |
| `api/status.json` | when it was last built, and counts |
| `api/unconfirmed.json` | single-source names, for research only, not for display |

A day file looks like:
```json
{
  "civil_date": "2026-10-29", "weekday": "Thursday",
  "hebrew_date_key": "18-Cheshvan", "hebrew_date_en": "18 Cheshvan 5787", "hebrew_date_he": "י״ח חשון תשפ״ז",
  "begins_evening_of": "2026-10-28",
  "yahrzeits": [ {"name_en": "...", "name_he": "...", "father_en": "...", "year_heb": "5747", "year": "1986", "who": "...", "sources": [...]} ],
  "history":   [ {"year_heb": "5699", "year": "1938", "en": "...", "sources": [...]} ],
  "counts": {"yahrzeits": 9, "history": 1}
}
```
The Hebrew date begins at nightfall the evening before the civil date (`begins_evening_of`). For a screen that switches at nightfall, show `tomorrow.json` after sunset.

Example: `curl -s https://<OWNER>.github.io/click613-yahrzeit-calendar/api/tomorrow.json`

## Run it on your own computer

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py --check            # validate data/
python scripts/build.py                    # build site/ for today
python scripts/build.py --date 2027-03-23  # build as if it were another day (testing)
cd site && python3 -m http.server 8000     # open http://localhost:8000
```

## How it runs by itself

`.github/workflows/daily.yml` runs:
- every day at 04:10 and 05:10 UTC (just after midnight New York time, in summer and in winter) and 15:00 UTC as a safety run;
- on every change to `data/`, `scripts/` or `web/` on `main`;
- by hand: **Actions -> Daily build and deploy -> Run workflow**.

Each run checks the data, builds, checks that `today.json` has today's New York date, deploys to Pages, and then fetches the live `today.json` to prove it is up.
If a run fails, the site keeps showing the last good build.

GitHub switches off scheduled workflows in a repo with no activity for 60 days; the last step of each scheduled run switches it back on, so this does not happen.

### Failure alerts
- **Built in:** GitHub e-mails the account that owns the workflow when a scheduled run fails. Check *Settings -> Notifications -> Actions -> "Send notifications for failed workflows only"* on the owner account (and on Chanoch's, once he is a collaborator and "watching" the repo).
- **Optional extra e-mail:** add these repository secrets (*Settings -> Secrets and variables -> Actions*) and the `alert` job sends its own e-mail on failure. Without them it does nothing.

| Secret | Example |
|---|---|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USERNAME` | the sending address |
| `SMTP_PASSWORD` | an app password for that address (never a normal password) |
| `ALERT_EMAIL_TO` | who gets the alert, comma-separated |

No secrets are stored in this repo.

## First-time setup (once)

1. Create the repo `click613-yahrzeit-calendar` on the Click613 GitHub account and push this folder to `main`.
2. *Settings -> Pages -> Build and deployment -> Source: **GitHub Actions***.
3. *Actions* tab -> enable workflows if asked -> **Daily build and deploy -> Run workflow**.
4. Open the Pages URL; open `api/today.json`.
5. Optional: *Settings -> Collaborators -> Add people* -> Chanoch. Optional: a custom domain such as `yahrzeits.click613.com` (*Settings -> Pages -> Custom domain*, plus a CNAME record at the DNS provider pointing to `<OWNER>.github.io`).

## Where the data came from

Built Oct 2026 by Click613 from: he.wikipedia Hebrew-date pages (rabbinic deaths) cross-checked against torahtots.com "This Month in Jewish History",
Wikidata death dates (converted with a Hebrew calendar), Luach Hatzibur Monsey yahrzeit tables, Or LaAm hillula lists, Matzav and other listed sources,
plus the nightly Click613 Gedolim Yahrzeits research. Each entry carries its own `sources`.
A small number of names from the nightly research (about 14, all in Cheshvan 5787) carry a note that they were checked against two sources when researched but the per-name source list was not saved; adding those sources is welcome.
