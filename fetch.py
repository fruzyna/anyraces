from urllib.request import urlopen, Request
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import tz
import json

from races import YEAR, AnyRaces, Race

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
TIME_FORMAT = '%I:%M %p'


def get_date_format(short_month=False, include_weekday=True, short_weekday=False):
    """Builds a the most common date format strings."""
    weekday = ''
    if (include_weekday):
        weekday = '%a, ' if short_weekday else '%A, '

    month = '%b' if short_month else '%B'
    return f'%Y {weekday}{month} %d'


def scrub_date(date_str):
    """Remove unnecessary information from a date string, replaces unknown times with noon."""
    return date_str.replace('.', '').replace(' ET', '').replace('Noon', '12:00 PM').replace('TBA', '12:00 PM').replace('TBD', '12:00 PM')


def parse_date(date_str, out_tz, short_month=False, include_weekday=True, short_weekday=False, date_separator='', in_tz='America/New_York'):
    """Takes an un-scrubbed date string and returns a time in central time."""
    date_str = f'{YEAR} {scrub_date(date_str)}'
    date_format = get_date_format(short_month, include_weekday, short_weekday)
    time_format = TIME_FORMAT
    if ':' not in date_str:
        time_format = '%I %p'

    if date_separator:
        date_separator += ' '

    # remove timezone at end
    if date_str.endswith(' EST'):
        date_str = date_str[:-4]
    elif date_str.endswith(' MST'):
        date_str = date_str[:-4]
        in_tz = 'America/Denver'
    elif date_str.endswith(' PST'):
        date_str = date_str[:-4]
        in_tz = 'America/Seattle'

    # build the datetime object
    dt = datetime.strptime(date_str, f'{date_format} {date_separator}{time_format}')
    if in_tz:
        dt = dt.replace(tzinfo=tz.gettz(in_tz)).astimezone(out_tz)
    else:
        dt = dt.replace(tzinfo=out_tz)

    return dt


def prevent_duplicates(name, previous_names):
    """Appends a number after a given name if it is already in the provided list."""
    i = 0
    n = name
    while n in previous_names:
        i += 1
        n = f'{name} {i}'

    return n


def process_espn_racing(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from espn.com/racing"""
    races = []

    # get rows of table
    series = ar.series[key]
    page = urlopen(series.schedule_url)
    html = page.read().decode('latin-1')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.table.find_all('tr')
    rows.pop(0)

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            # combine date and time, then interpret
            date = ''
            for s in cells[0].strings:
                if date:
                    date += ' '
                date += s

            if date != 'DATE':
                dt = parse_date(date, ar.time_zone, short_month=True, short_weekday=True)

                # use track as race name
                race = ''
                skip = False
                for s in cells[1].strings:
                    if not race:
                        race = s
                    # interpret postponed dates
                    elif s.startswith('**Race postponed to '):
                        dt = parse_date(s[s.index(' to ')+4:], ar.time_zone, short_month=True, include_weekday=False, date_separator='at')
                    elif 'Practice' in s or 'Qualifying' in s or 'Shootout' in s:
                        skip = True
                    elif 'Sprint' in s:
                        race += ' (Sprint)'

                # remove annoying extract cup series text
                if race.startswith('NASCAR') and ' at ' in race:
                    start = race.index(' at ') + 4
                    race = race[start:]
                elif race.startswith('NASCAR'):
                    start = race.upper().index('SERIES') + 7
                    race = race[start:]

                if len(cells) >= 3:
                    tv = list(cells[2].strings)[0]
                    if tv is None:
                        tv = 'FOX'
                    elif tv == 'USA Net':
                        tv = 'USA'
                    elif tv == 'Prime Video':
                        tv = 'Prime'
                else:
                    tv = ''

                # combine into EventBot compatible dictionary
                if not skip:
                    races.append(Race(race, key, dt, tv))

    return races


def process_espn_f1(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from espn.com/f1"""
    races = []

    # get rows of table
    series = ar.series[key]
    page = urlopen(series.schedule_url)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.tbody.find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        # interpret date time
        date = cells[2].string
        if ' - ' in date:
            dt = parse_date(date, ar.time_zone, short_month=True, include_weekday=False, date_separator='-')

            # interpret race name
            race = ''
            for s in cells[1].strings:
                if not race:
                    race = s

            tv = cells[3].string
            if tv is None:
                tv = 'ESPN?'
            else:
                tv = tv.replace('/ESPN+', '')

            # combine into EventBot compatible dictionary
            races.append(Race(race, key, dt, tv))

    return races


def process_imsa(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from imsa.com"""
    races = []

    # get rows of table
    series = ar.series[key]
    req = Request(series.schedule_url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('div', class_='rich-text-component-container')
    rows.pop(0)

    for row in rows:
        name = row.find('a', class_='onTv-event-title').string.strip().split(' (')[0]
        if name != 'WeatherTech Championship Qualifying':
            date = scrub_date(row.find('span', class_='date-display-single').string.split(' -')[0])
            dt = datetime.strptime(date, f'%A, %B %d, %Y – {TIME_FORMAT}')
            dt = dt.replace(tzinfo=tz.gettz('America/New_York')).astimezone(ar.time_zone)

            # determine TV channel by image
            tvimg = row.img['src'].upper()
            if 'IMSATV' in tvimg:
                tv = 'IMSAtv'
            elif 'PEACOCK' in tvimg:
                tv = 'Peacock'
            elif 'CNBC' in tvimg:
                tv = 'CNBC'
            elif 'NBC' in tvimg:
                tv = 'NBC'
            elif 'USA' in tvimg:
                tv = 'USA'
            elif 'YOUTUBE' in tvimg:
                tv = 'YouTube'
            else:
                tv = 'Unknown'

            races.append(Race(name, key, dt, tv))

    # remove duplicate listings
    remove = []
    for i in range(len(races)):
        if i + 1 < len(races):
            a = races[i]
            b = races[i+1]
            if a.name == b.name:
                remove.append(i)
                b.time = a.time if a.time < b.time else b.time
                b.channel = ' '.join(set(f'{a.channel} {b.channel}'.split()))

    for i in sorted(remove, reverse=True):
        del races[i]

    return races


def process_indy(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from indycar.com"""
    races = []

    # get rows of table
    series = ar.series[key]
    page = urlopen(series.schedule_url)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find('section', class_='card-repeater').find_all('div', class_='event-card')

    for item in items:
        name = item.find('h3', class_='event-card-title').string.strip().replace('INDY NXT by Firestone at', '')
        date = item.find('div', class_='event-card-header-date').string.strip()
        time = item.find('div', class_='event-card-header-time').string.strip()
        tv = item.find('div', class_='event-card-header-network').img['alt'].strip()

        date = scrub_date(f'{date} {time}')
        dt = parse_date(date, ar.time_zone, short_month=True, include_weekday=False)

        # combine into EventBot compatible dictionary
        races.append(Race(name, key, dt, tv))

    return races


def process_arca(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from arcaracing.com"""
    races = []

    # get rows of table
    series = ar.series[key]
    req = Request(series.schedule_url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.table.find_all('tr')
    rows.pop(0)

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[0].string.replace('Sept', 'Sep')
            time = cells[3].string.replace('*', '')
            if '(Delayed broadcast at ' in time:
                time = time[time.index('at') + 3:-1]

            date = f'{date} {time}'

            try:
                dt = parse_date(date, ar.time_zone, short_month=True)
            except ValueError:
                dt = parse_date(date, ar.time_zone)

            # use track as race name
            race = prevent_duplicates(cells[1].string, [r.name for r in races])

            tv = cells[4].string.split()[0]
            stream = cells[5].string
            if tv == '—':
                tv = stream

            races.append(Race(race, key, dt, tv))

            if tv != stream and stream != 'Fox Sports App':
                races[-1].channel += ' ' + stream.replace(' / Fox Sports App', '')

    return races


def process_nascar_ca(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from nascar.ca"""
    races = []

    # get rows of table
    series = ar.series[key]
    req = Request(series.schedule_url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.table.find_all('tr')
    rows.pop(0)

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[1].find('div', 'event-date').string
            time = cells[1].find('div', 'event-time').string

            dt = parse_date(f'{date} {time}', ar.time_zone, short_month=True)

            # use track as race name
            race = prevent_duplicates(cells[0].find('div', 'race-name').string, [r.name for r in races])

            races.append(Race(race, key, dt, 'FloRacing'))

    return races


def process_nascar_mod(ar: AnyRaces, key: str) -> list:
    """Fetch race schedule from nascar.com"""
    races = []

    # get rows of table
    series = ar.series[key]
    req = Request(series.schedule_url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.table.find_all('tr')
    rows.pop(0)

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[1].contents[0].string.strip()
            time = cells[1].find('p', 'race-time').string   
            date = f'{date} {time}'

            try:
                dt = parse_date(date, ar.time_zone)
            except ValueError:
                dt = parse_date(date.replace('Sept', 'Sep'), ar.time_zone, short_month=True)

            # use track as race name
            race = cells[0].find('span', 'race-name-span').string.replace('*', '').replace('^', '').strip()

            races.append(Race(race, key, dt, 'FloRacing'))

    return races


def process_nascar_nationals(ar: AnyRaces, key: str) -> list:
    """Fetch official national NASCAR series' schedules from NASCAR.com."""
    series_tab = {
        'NCS': 'series_1',
        'NOAPS': 'series_2',
        'NCTS': 'series_3'
    }

    series = ar.series[key]
    page = urlopen(series.schedule_url)
    data = json.load(page)

    if key not in series_tab or series_tab[key] not in data:
        return []

    def fromisoformat(date: str):
        return datetime.fromisoformat(date).replace(tzinfo=tz.gettz('America/New_York')).astimezone(ar.time_zone)

    races = []
    for r in data[series_tab[key]]:
        name = r['race_name'].replace('NASCAR ', '').replace('CRAFTSMAN Truck Series ', '').replace('O\'Reilly Auto Parts Series ', '').replace('Race at ', '')
        if ' by ' in name:
            words = name.split()
            name = ' '.join(words[:words.index('by') - 1])

        races.append(Race(name, key, fromisoformat(r['race_date']), r['television_broadcaster']))

    return races


def generate_races(ar, key):
    """Generate the list of races by processing data from the given URL."""
    races = []
    schedule_url = ar.series[key].schedule_url
    if 'cf.nascar.com' in schedule_url:
        races = process_nascar_nationals(ar, key)
    elif 'espn.com/racing' in schedule_url:
        races = process_espn_racing(ar, key)
    elif 'espn.com/f1' in schedule_url:
        races = process_espn_f1(ar, key)
    elif 'indycar.com' in schedule_url:
        races = process_indy(ar, key)
    elif 'imsa.com' in schedule_url:
        races = process_imsa(ar, key)
    elif 'arcaracing.com' in schedule_url:
        races = process_arca(ar, key)
    elif 'nascar.ca' in schedule_url:
        races = process_nascar_ca(ar, key)
    elif 'nascar.com' in schedule_url and 'modified' in schedule_url:
        races = process_nascar_mod(ar, key)

    return races


def fetch_races(ar):
    # build a list of races from each series
    races = []
    for k in ar.series:
        name = ar.series[k].name
        try:
            races.extend(generate_races(ar, k))
        except HTTPError:
            print(f'Unable to fetch {name}')
        except Exception as e:
            print(f'Unable to scrape {name}:', e)

    print('Fetched', len(races), 'total races')
    return races


def merge_races(old_races, new_races):
    # merge with the existing races
    merged_races = new_races.copy()
    for race in old_races:
        matches = [r for r in new_races if r == race]
        if not matches:
            merged_races.append(race)
            print('Restoring', race.series, race.name)
        elif matches[0].time != race.time:
            print(race.series, race.name, 'updated from', race.time, 'to', matches[0].time)

    print('Merged into', len(merged_races), 'total races')
    return merged_races


if __name__ == '__main__':
    ar = AnyRaces()
    ar.read_config()

    races = ar.read_manual_entries()
    races += fetch_races(ar)
    races.sort(key=lambda r: r.time)

    old_races = ar.read_races()
    races = merge_races(old_races, races)

    ar.write_races(races)
