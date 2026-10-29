#!/usr/bin/env python3
"""Click613 Yahrzeit Calendar — static site + API builder.

Reads  data/yahrzeits.json, data/history.json, data/unconfirmed.json
Writes site/  (index.html, assets/, api/...) ready for GitHub Pages.

Usage:
  python scripts/build.py                 # build with today's date (America/New_York)
  python scripts/build.py --date 2026-11-05   # pretend "today" is this civil date (testing)
  python scripts/build.py --check         # validate the data files only (used on pull requests)

Only dependency: pyluach (Hebrew calendar).  pip install -r requirements.txt
"""
import argparse, csv, datetime, io, json, os, re, shutil, sys
from zoneinfo import ZoneInfo
from pyluach import dates as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
WEB = os.path.join(ROOT, 'web')
OUT = os.path.join(ROOT, 'site')
TZ = ZoneInfo('America/New_York')
DAYS_BACK, DAYS_AHEAD = 7, 420          # api/day/<date>.json window
ICS_DAYS = 400

# month keys used in the data, in Hebrew-year order (Tishrei first)
MONTH_KEYS = ['Tishrei', 'Cheshvan', 'Kislev', 'Teves', 'Shevat', 'Adar', 'Adar-I', 'Adar-II', 'Nisan', 'Iyar', 'Sivan', 'Tammuz', 'Av', 'Elul']
MNUM = {'Nisan': 1, 'Iyar': 2, 'Sivan': 3, 'Tammuz': 4, 'Av': 5, 'Elul': 6, 'Tishrei': 7, 'Cheshvan': 8, 'Kislev': 9,
        'Teves': 10, 'Shevat': 11, 'Adar': 12, 'Adar-I': 12, 'Adar-II': 13}
MONTH_HE = {'Nisan': 'ניסן', 'Iyar': 'אייר', 'Sivan': 'סיון', 'Tammuz': 'תמוז', 'Av': 'אב', 'Elul': 'אלול', 'Tishrei': 'תשרי',
            'Cheshvan': 'חשון', 'Kislev': 'כסלו', 'Teves': 'טבת', 'Shevat': 'שבט', 'Adar': 'אדר', 'Adar-I': 'אדר א׳', 'Adar-II': 'אדר ב׳'}
MONTH_DAYS = {'Tishrei': 30, 'Cheshvan': 30, 'Kislev': 30, 'Teves': 29, 'Shevat': 30, 'Adar': 29, 'Adar-I': 30, 'Adar-II': 29,
              'Nisan': 30, 'Iyar': 29, 'Sivan': 30, 'Tammuz': 29, 'Av': 30, 'Elul': 29}
NUM_HE = {1: 'א', 2: 'ב', 3: 'ג', 4: 'ד', 5: 'ה', 6: 'ו', 7: 'ז', 8: 'ח', 9: 'ט', 10: 'י', 20: 'כ', 30: 'ל'}
KEY_RE = re.compile(r'^(\d{1,2})-(' + '|'.join(MONTH_KEYS) + r')$')


def is_leap(y):
    return (7 * y + 1) % 19 < 7


def heb_day(n):
    if n == 15: return 'ט״ו'
    if n == 16: return 'ט״ז'
    t, o = (n // 10) * 10, n % 10
    s = (NUM_HE.get(t, '') if t else '') + (NUM_HE.get(o, '') if o else '')
    return (s[:-1] + '״' + s[-1]) if len(s) > 1 else s + '׳'


def month_len(y, m):
    last = 13 if is_leap(y) else 12
    if m == 6: ny, nm = y + 1, 7
    elif m == last: ny, nm = y, 1
    else: ny, nm = y, m + 1
    return (D.HebrewDate(ny, nm, 1).to_pydate() - D.HebrewDate(y, m, 1).to_pydate()).days


def key_month_of(hdate):
    """Data key month name for a pyluach HebrewDate."""
    if hdate.month == 12: return 'Adar-I' if is_leap(hdate.year) else 'Adar'
    if hdate.month == 13: return 'Adar-II'
    return [k for k, v in MNUM.items() if v == hdate.month and k not in ('Adar', 'Adar-I', 'Adar-II')][0]


def observed(person, key, hyear):
    """(month, day) on which this yahrzeit is kept in Hebrew year hyear (hebcal getYahrzeit rules)."""
    d, mk = key.split('-', 1)
    day, m = int(d), MNUM[mk]
    leap = is_leap(hyear)
    if mk == 'Adar':
        m = 13 if (leap and person.get('adar') == 'II') else 12      # plain-Adar yahrzeit is kept in Adar I in a leap year
    elif mk == 'Adar-I':
        m = 12
        if not leap and day == 30: return 11, 30                        # 30 Adar I in a plain year -> 30 Shevat
    elif mk == 'Adar-II':
        m = 13 if leap else 12
    if day == 30 and m in (8, 9):                                        # 30 Cheshvan / 30 Kislev
        try: dy = int(person.get('year_heb') or 0)
        except ValueError: dy = 0
        if dy and month_len(dy + 1, m) == 29: return m, 29
        if month_len(hyear, m) == 29: return m + 1, 1
    if day == 30 and month_len(hyear, m) == 29:
        return (m + 1, 1) if m != 6 else (7, 1)
    return m, day


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def validate(Y, H, U):
    errs = []
    for label, doc, kind in (('yahrzeits.json', Y, 'p'), ('history.json', H, 'e'), ('unconfirmed.json', U, 'p')):
        if not isinstance(doc.get('dates'), dict): errs.append(f'{label}: missing "dates" object'); continue
        for k, lst in doc['dates'].items():
            m = KEY_RE.match(k)
            if not m: errs.append(f'{label}: bad date key "{k}" (use e.g. "15-Cheshvan")'); continue
            if not 1 <= int(m.group(1)) <= MONTH_DAYS[m.group(2)]: errs.append(f'{label}: {k} day out of range')
            if not isinstance(lst, list): errs.append(f'{label}: {k} must be a list'); continue
            for i, x in enumerate(lst):
                where = f'{label} {k} #{i+1}'
                if kind == 'p':
                    if not (x.get('name_he') or x.get('name_en')): errs.append(f'{where}: needs name_he or name_en')
                    if label == 'yahrzeits.json':
                        if not x.get('sources'): errs.append(f'{where} ({x.get("name_en")}): needs "sources"')
                        if x.get('adar') not in (None, 'I', 'II'): errs.append(f'{where}: adar must be "I", "II" or absent')
                else:
                    if not (x.get('en') or x.get('he')): errs.append(f'{where}: needs "en" or "he"')
                    if not x.get('sources'): errs.append(f'{where}: needs "sources"')
                for s in x.get('sources') or []:
                    if not isinstance(s, dict) or not s.get('name'): errs.append(f'{where}: each source needs a "name"')
    return errs


def clean(x):
    return {k: v for k, v in x.items() if v not in (None, '', [])}


def person_line(p):
    s = p.get('name_en') or p.get('name_he') or ''
    if p.get('father_en'): s += f", son of {p['father_en']}"
    yrs = ' / '.join(v for v in (p.get('year_heb'), p.get('year')) if v)
    if yrs: s += f' ({yrs})'
    if p.get('name_he'): s += f" | {p['name_he']}"
    if p.get('who'): s += f" — {p['who']}"
    return s


def event_line(e):
    yrs = ' / '.join(v for v in (e.get('year_heb'), e.get('year_note'), e.get('year')) if v)
    return (f'{yrs}: ' if yrs else '') + (e.get('en') or e.get('he') or '')


def ics_escape(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def ics_fold(line):
    b = line.encode('utf-8'); out = []
    while len(b) > 74:
        cut = 74
        while cut > 0 and (b[cut] & 0xC0) == 0x80: cut -= 1
        out.append(b[:cut].decode('utf-8')); b = b' ' + b[cut:]
    out.append(b.decode('utf-8'))
    return '\r\n'.join(out)


def wjson(path, obj, pretty=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        if pretty: json.dump(obj, f, ensure_ascii=False, indent=1)
        else: json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def build(today):
    Y, H, U = load('yahrzeits.json'), load('history.json'), load('unconfirmed.json')
    errs = validate(Y, H, U)
    if errs:
        print('DATA ERRORS:\n  ' + '\n  '.join(errs[:50]), file=sys.stderr); sys.exit(2)
    gen = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    Yd, Hd, Ud = Y['dates'], H['dates'], U['dates']
    # strip internal fields for output
    pub_p = lambda p: clean({k: v for k, v in p.items() if k not in ('origin',)})
    pub_e = lambda e: clean({k: v for k, v in e.items() if k not in ('origin',)})

    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree(WEB, OUT)
    api = os.path.join(OUT, 'api')

    # ---- observed index: (hyear, month, day) -> people
    first = today - datetime.timedelta(days=DAYS_BACK)
    last = today + datetime.timedelta(days=max(DAYS_AHEAD, ICS_DAYS))
    hy0 = D.GregorianDate.from_pydate(first).to_heb().year
    hy1 = D.GregorianDate.from_pydate(last).to_heb().year
    obs = {}
    for hy in range(hy0, hy1 + 1):
        for k, lst in Yd.items():
            for p in lst:
                m, d = observed(p, k, hy)
                obs.setdefault((hy, m, d), []).append((k, p))

    def history_for(hd):
        mk = key_month_of(hd)
        if mk == 'Adar-II':      # leap year: plain-Adar history events (Purim's Adar) show in Adar II
            return Hd.get(f'{hd.day}-Adar', []) + Hd.get(f'{hd.day}-Adar-II', [])
        return Hd.get(f'{hd.day}-{mk}', [])

    def day_doc(d):
        hd = D.GregorianDate.from_pydate(d).to_heb()
        mk = key_month_of(hd)
        people = [pub_p(p) | {'listed_under': k} if k != f'{hd.day}-{mk}' else pub_p(p) for k, p in obs.get((hd.year, hd.month, hd.day), [])]
        events = [pub_e(e) for e in history_for(hd)]
        return {
            'civil_date': d.isoformat(),
            'weekday': d.strftime('%A'),
            'hebrew_date_key': f'{hd.day}-{mk}',
            'hebrew_date_en': f"{hd.day} {mk.replace('-', ' ')} {hd.year}",
            'hebrew_date_he': hd.hebrew_date_string(),
            'begins_evening_of': (d - datetime.timedelta(days=1)).isoformat(),
            'note': 'The Hebrew date begins at nightfall on the evening before the civil date.',
            'yahrzeits': people,
            'history': events,
            'counts': {'yahrzeits': len(people), 'history': len(events)},
        }

    # ---- per civil day
    d = first
    while d <= today + datetime.timedelta(days=DAYS_AHEAD):
        wjson(f'{api}/day/{d.isoformat()}.json', day_doc(d))
        d += datetime.timedelta(days=1)
    tdoc, mdoc = day_doc(today), day_doc(today + datetime.timedelta(days=1))
    wjson(f'{api}/today.json', tdoc | {'generated': gen}, pretty=True)
    wjson(f'{api}/tomorrow.json', mdoc | {'generated': gen}, pretty=True)

    # ---- per Hebrew date (canonical keys, as stored)
    all_keys = [f'{n}-{m}' for m in MONTH_KEYS for n in range(1, MONTH_DAYS[m] + 1)]
    for k in all_keys:
        n, mk = k.split('-', 1)
        doc = {'hebrew_date_key': k, 'hebrew_date_he': f'{heb_day(int(n))} {MONTH_HE[mk]}',
               'yahrzeits': [pub_p(p) for p in Yd.get(k, [])], 'history': [pub_e(e) for e in Hd.get(k, [])]}
        if mk == 'Adar':
            doc['note'] = 'Adar of a plain year. In a leap year these yahrzeits are kept in Adar I, except names marked "adar": "II".'
        if mk == 'Adar-II':
            doc['also_kept_in_adar_ii'] = [pub_p(p) for p in Yd.get(f'{n}-Adar', []) if p.get('adar') == 'II']
        doc['counts'] = {'yahrzeits': len(doc['yahrzeits']), 'history': len(doc['history'])}
        wjson(f'{api}/date/{k}.json', doc)

    # ---- per month (for the browse page) + search index
    for mk in MONTH_KEYS:
        wjson(f'{api}/month/{mk}.json', {'month': mk, 'month_he': MONTH_HE[mk], 'days': MONTH_DAYS[mk],
              'yahrzeits': {k: [pub_p(p) for p in v] for k, v in Yd.items() if k.split('-', 1)[1] == mk and v},
              'history': {k: [pub_e(e) for e in v] for k, v in Hd.items() if k.split('-', 1)[1] == mk and v}})
    search = []
    for k, v in Yd.items():
        for p in v: search.append(['y', k, p.get('name_en') or '', p.get('name_he') or '', p.get('father_en') or '', p.get('year_heb') or '', p.get('year') or '', (p.get('who') or '')[:160]])
    for k, v in Hd.items():
        for e in v: search.append(['h', k, (e.get('en') or '')[:200], e.get('he') or '', '', e.get('year_heb') or '', e.get('year') or ''])
    wjson(f'{api}/search.json', search)

    # ---- full files
    ny, nh, nu = (sum(len(v) for v in x.values()) for x in (Yd, Hd, Ud))
    yfull = {'title': 'Click613 Gedolim Yahrzeits', 'generated': gen, 'count': ny, 'note': Y.get('note'),
             'by_hebrew_date': {k: [pub_p(p) for p in v] for k, v in Yd.items()}}
    hfull = {'title': 'Click613 Jewish History of the Day', 'generated': gen, 'count': nh, 'note': H.get('note'),
             'by_hebrew_date': {k: [pub_e(e) for e in v] for k, v in Hd.items()}}
    wjson(f'{api}/yahrzeits.json', yfull)
    wjson(f'{api}/history.json', hfull)
    wjson(f'{api}/unconfirmed.json', {'title': 'UNCONFIRMED yahrzeits (single source or conflicting) - do not publish as fact', 'generated': gen,
          'count': nu, 'by_hebrew_date': {k: [pub_p(p) for p in v] for k, v in Ud.items()}})
    wjson(f'{api}/all.json', {'title': 'Click613 Yahrzeit Calendar - everything', 'generated': gen,
          'counts': {'yahrzeits': ny, 'history': nh}, 'yahrzeits': yfull['by_hebrew_date'], 'history': hfull['by_hebrew_date']})

    # ---- CSV
    def srcs(x): return ' | '.join(s.get('name', '') + (f" <{s['url']}>" if s.get('url') else '') for s in x.get('sources') or [])
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(['hebrew_date', 'name_en', 'name_he', 'father_en', 'father_he', 'year_heb', 'year_civil', 'who', 'adar', 'burial', 'sources'])
    for k, v in Yd.items():
        for p in v:
            w.writerow([k, p.get('name_en', ''), p.get('name_he', ''), p.get('father_en', ''), p.get('father_he', ''), p.get('year_heb', ''),
                        p.get('year', ''), p.get('who', ''), p.get('adar', '') or '', (p.get('burial') or {}).get('en', ''), srcs(p)])
    open(f'{api}/yahrzeits.csv', 'w', encoding='utf-8-sig', newline='').write(buf.getvalue())
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(['hebrew_date', 'year_heb', 'year_civil', 'event_en', 'event_he', 'sources'])
    for k, v in Hd.items():
        for e in v:
            w.writerow([k, e.get('year_heb') or e.get('year_note') or '', e.get('year', ''), e.get('en', ''), e.get('he', '') or '', srcs(e)])
    open(f'{api}/history.csv', 'w', encoding='utf-8-sig', newline='').write(buf.getvalue())

    # ---- ICS (one all-day event per civil day that has yahrzeits)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Click613//Yahrzeit Calendar//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
         'X-WR-CALNAME:Click613 Yahrzeits', 'X-WR-TIMEZONE:America/New_York', 'REFRESH-INTERVAL;VALUE=DURATION:PT12H', 'X-PUBLISHED-TTL:PT12H']
    d = today - datetime.timedelta(days=DAYS_BACK)
    nev = 0
    while d <= today + datetime.timedelta(days=ICS_DAYS):
        doc = day_doc(d)
        if doc['yahrzeits'] or doc['history']:
            names = [p.get('name_en') or p.get('name_he') for p in doc['yahrzeits']]
            summ = f"Yahrzeits {doc['hebrew_date_en']}: " + '; '.join(names[:3]) + (f' +{len(names)-3} more' if len(names) > 3 else '') if names else f"Jewish history {doc['hebrew_date_en']}"
            desc = f"{doc['hebrew_date_he']} (begins the evening of {doc['begins_evening_of']})\n\nYAHRZEITS\n" + '\n'.join('• ' + person_line(p) for p in doc['yahrzeits'])
            if doc['history']: desc += '\n\nJEWISH HISTORY\n' + '\n'.join('• ' + event_line(e) for e in doc['history'])
            desc += '\n\nClick613'
            nxt = d + datetime.timedelta(days=1)
            L += ['BEGIN:VEVENT', f'UID:click613-yahrzeits-{d.isoformat()}@click613.com', f'DTSTAMP:{stamp}',
                  f'DTSTART;VALUE=DATE:{d.strftime("%Y%m%d")}', f'DTEND;VALUE=DATE:{nxt.strftime("%Y%m%d")}',
                  ics_fold('SUMMARY:' + ics_escape(summ)), ics_fold('DESCRIPTION:' + ics_escape(desc)), 'TRANSP:TRANSPARENT', 'END:VEVENT']
            nev += 1
        d += datetime.timedelta(days=1)
    L.append('END:VCALENDAR')
    open(f'{api}/calendar.ics', 'w', encoding='utf-8', newline='').write('\r\n'.join(L) + '\r\n')

    status = {'generated': gen, 'today': today.isoformat(), 'today_hebrew': tdoc['hebrew_date_en'],
              'counts': {'yahrzeits': ny, 'history': nh, 'unconfirmed': nu, 'hebrew_dates_with_yahrzeits': sum(1 for v in Yd.values() if v),
                         'ics_events': nev},
              'day_files': {'first': first.isoformat(), 'last': (today + datetime.timedelta(days=DAYS_AHEAD)).isoformat()}}
    wjson(f'{api}/status.json', status, pretty=True)
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    print(json.dumps(status))
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='civil date to treat as today (YYYY-MM-DD)')
    ap.add_argument('--check', action='store_true', help='only validate data/*.json')
    a = ap.parse_args()
    if a.check:
        errs = validate(load('yahrzeits.json'), load('history.json'), load('unconfirmed.json'))
        if errs: print('DATA ERRORS:\n  ' + '\n  '.join(errs), file=sys.stderr); sys.exit(2)
        print('data OK'); return
    today = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(TZ).date()
    build(today)


if __name__ == '__main__':
    main()
