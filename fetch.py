from urllib.request import urlopen, Request
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import tz
import glob
import json


HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"}


class Series(object):

    def __init__(self, name: str, schedule_url: str, tags=[]):
        self.name = name
        self.schedule_url = schedule_url
        self.tags = tags
        self.races = []

    def generate_races(self):
        """Generate the list of races by processing data from the given URL."""
        if 'espn.com/racing' in self.schedule_url:
            self.races = process_espn_racing(self.schedule_url, self)
        elif 'espn.com/f1' in self.schedule_url:
            self.races = process_espn_f1(self.schedule_url, self)
        elif 'indycar.com' in self.schedule_url:
            self.races = process_indy(self.schedule_url, self)
        elif 'imsa.com' in self.schedule_url:
            self.races = process_imsa(self.schedule_url, self)
        elif 'arcaracing.com' in self.schedule_url:
            self.races = process_arca(self.schedule_url, self)
        elif 'nascar.ca' in self.schedule_url:
            self.races = process_nascar_ca(self.schedule_url, self)
        elif 'nascar.com' in self.schedule_url and 'modified' in self.schedule_url:
            self.races = process_nascar_mod(self.schedule_url, self)
        elif 'fiawec.com' in self.schedule_url:
            self.races = process_wec(self.schedule_url, self)


class Race(object):

    def __init__(self, name: str, series: Series, time: datetime, channel: str):
        self.name = name.replace("’", "'")
        self.time = time
        self.channel = channel.replace(' ', '')
        self.series = series.name
        self.tags = series.tags

    def build_row(self):
        """Builds a CSV row of data from the object."""
        tags = ' '.join(self.tags)
        date = self.time.strftime('%m/%d')
        time = self.time.strftime('%H:%M')
        return ','.join([self.name, self.series, date, time, self.channel, tags])


series = [
    Series('NPS', 'https://www.nascar.ca/schedule/', ['NASCAR', 'Stock']),
    Series('NWMT', 'https://www.nascar.com/nascar-whelen-modified-tour-schedule/', ['NASCAR', 'Stock', 'Open-Wheel']),
    #Series('NCS', 'https://www.espn.com/racing/schedule', ['NASCAR', 'Stock', 'Premier']),
    #Series('NXS', 'https://www.espn.com/racing/schedule/_/series/xfinity', ['NASCAR', 'Stock']),
    #Series('NCTS', 'https://www.espn.com/racing/schedule/_/series/camping', ['NASCAR', 'Stock']),
    Series('ARCA', 'https://www.arcaracing.com/2024-race-broadcast-schedule/', ['Stock']),
    Series('INDY', 'https://www.espn.com/racing/schedule/_/series/indycar', ['IndyCar', 'Open-Wheel', 'Premier']),
    Series('NXT', 'https://www.indycar.com/INDYNXT/Schedule', ['IndyCar', 'Open-Wheel']),
    Series('F1', 'https://www.espn.com/f1/schedule', ['Grand-Prix', 'Open-Wheel', 'Premier']),
    #Series('F1', 'https://www.espn.com/racing/schedule/_/series/f1', ['Grand-Prix', 'Open-Wheel', 'Premier']),
    Series('WTSC', 'https://www.imsa.com/weathertech/tv-streaming-schedule/', ['IMSA', 'GT', 'Prototype', 'Premier']),
    Series('PILOT', 'https://www.imsa.com/michelinpilotchallenge/tv-streaming-schedule/', ['IMSA', 'GT', 'Touring']),
    Series('WEC', 'https://www.fiawec.com/en/race/show/4929', ['GT', 'Prototype'])
]

YEAR = now = datetime.now().year
TIME_FORMAT = '%I:%M %p'
TIME_ZONE = tz.gettz('America/Chicago')


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


def parse_date(date_str, short_month=False, include_weekday=True, short_weekday=False, date_separator='', eastern_time=True):
    """Takes an un-scrubbed date string and returns a time in central time."""
    date_str = f'{YEAR} {scrub_date(date_str)}'
    date_format = get_date_format(short_month, include_weekday, short_weekday)
    time_format = TIME_FORMAT
    if ':' not in date_str:
        time_format = '%I %p'

    if date_separator:
        date_separator += ' '

    dt = datetime.strptime(date_str, f'{date_format} {date_separator}{time_format}')
    if eastern_time:
        dt = dt.replace(tzinfo=tz.gettz('America/New_York')).astimezone(TIME_ZONE)
    else:
        dt = dt.replace(tzinfo=TIME_ZONE)

    return dt


def process_espn_racing(url: str, series: Series) -> list:
    """Fetch race schedule from espn.com/racing"""
    races = []

    # get rows of table
    page = urlopen(url)
    html = page.read().decode('latin-1')
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.table.find_all("tr")
    rows.pop(0)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            # combine date and time, then interpret
            date = ''
            for s in cells[0].strings:
                if date:
                    date += ' '
                date += s

            if date != 'DATE':
                dt = parse_date(date, short_month=True, short_weekday=True)

                # use track as race name
                race = ''
                skip = False
                for s in cells[1].strings:
                    if not race:
                        race = s
                    # interpret postponed dates
                    elif s.startswith("**Race postponed to "):
                        dt = parse_date(s[s.index(' to ')+4:], short_month=True, include_weekday=False, date_separator='at')
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
                    tv = cells[2].string
                    if tv is None:
                        tv = ''
                    elif tv == 'USA Net':
                        tv = 'USA'
                    elif tv == 'Prime Video':
                        tv = 'Prime'
                else:
                    tv = ''

                # combine into EventBot compatible dictionary
                if not skip:
                    races.append(Race(race, series, dt, tv))

    return races


def process_espn_f1(url: str, series: Series) -> list:
    """Fetch race schedule from espn.com/f1"""
    races = []

    # get rows of table
    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.tbody.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        # interpret date time
        date = cells[2].string
        if " - " in date:
            dt = parse_date(date, short_month=True, include_weekday=False, date_separator='-')

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
            races.append(Race(race, series, dt, tv))

    return races


def process_imsa(url: str, series: Series) -> list:
    """Fetch race schedule from imsa.com"""
    races = []

    # get rows of table
    req = Request(url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("div", class_="rich-text-component-container")
    rows.pop(0)

    for row in rows:
        name = row.find('a', class_='onTv-event-title').string.strip().split(' (')[0]
        date = scrub_date(row.find("span", class_='date-display-single').string.split(' -')[0])
        dt = datetime.strptime(date, f'%A, %B %d, %Y – {TIME_FORMAT}')
        dt = dt.replace(tzinfo=tz.gettz('America/New_York')).astimezone(TIME_ZONE)

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

        races.append(Race(name, series, dt, tv))

    # remove duplicate listings
    remove = []
    for i in range(len(races)):
        if i + 1 < len(races):
            if abs(races[i].time - races[i+1].time) < timedelta(minutes=30) and races[i].series == races[i+1].series:
                remove.append(i)
                races[i+1].time = races[i].time
                races[i+1].channel = f"{races[i].channel} {races[i+1].channel}"

    for i in sorted(remove, reverse=True):
        del races[i]

    return races


def process_indy(url: str, series: Series) -> list:
    """Fetch race schedule from indycar.com"""
    races = []

    # get rows of table
    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("li", class_="schedule-list__item")

    for item in items:
        name = item.find('a', class_='schedule-list__title').span.string.strip()
        date = item.find('div', class_='schedule-list__date')
        # indy replaces past races with the winner
        if date:
            month = date.contents[0].strip()
            day = date.find('span', class_='schedule-list__date-day').string.strip()
            time = item.find('span', class_='timeEst').string.strip()
            date = scrub_date(f'{YEAR} {month} {day} {time}')

            dt = parse_date(f'{month} {day} {time}', short_month=True, include_weekday=False)

            # determine TV channel by image
            tv = item.find("div", class_='schedule-list__broadcast-logos').a.img['alt']

            # combine into EventBot compatible dictionary
            races.append(Race(name, series, dt, tv))

    return races


def process_arca(url: str, series: Series) -> list:
    """Fetch race schedule from arcaracing.com"""
    races = []

    # get rows of table
    req = Request(url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.table.find_all("tr")
    rows.pop(0)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[0].string.replace('Sept', 'Sep')
            time = cells[3].string.replace('*', '')
            date = f'{date} {time}'

            try:
                dt = parse_date(date, short_month=True)
            except ValueError:
                dt = parse_date(date)

            # use track as race name
            race = cells[1].string

            tv = cells[4].string
            stream = cells[5].string
            if tv == '—':
                tv = stream

            races.append(Race(race, series, dt, tv))

            if tv != stream and stream != 'Fox Sports App':
                races[-1].channel += ' ' + stream.replace(' / Fox Sports App', '')

    return races


def process_nascar_ca(url: str, series: Series) -> list:
    """Fetch race schedule from arcaracing.com"""
    races = []

    # get rows of table
    req = Request(url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.table.find_all("tr")
    rows.pop(0)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[1].find('div', 'event-date').string
            time = cells[1].find('div', 'event-time').string

            dt = parse_date(f'{date} {time}', short_month=True)

            # use track as race name
            race = cells[0].find('div', 'race-name').string

            races.append(Race(race, series, dt, 'FloRacing'))

    return races


def process_nascar_mod(url: str, series: Series) -> list:
    """Fetch race schedule from arcaracing.com"""
    races = []

    # get rows of table
    req = Request(url, headers=HEADERS)
    page = urlopen(req)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.table.find_all("tr")
    rows.pop(0)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 5:
            # combine date and time, then interpret
            date = cells[1].contents[0].string.strip()
            time = cells[1].find('p', 'race-time').string   
            date = f'{date} {time}'

            try:
                dt = parse_date(date)
            except ValueError:
                dt = parse_date(date.replace('Sept', 'Sep'), short_month=True)

            # use track as race name
            race = cells[0].find('span', 'race-name-span').string.strip()

            races.append(Race(race, series, dt, 'FloRacing'))

    return races


def process_wec(url: str, series: Series) -> list:
    """Fetch race schedule from fiawec.com"""
    races = []

    parts = url.split('/')
    index = int(parts[-1])
    base = '/'.join(parts[:-1])

    while True:
        req = Request(f'{base}/{index}', headers=HEADERS)
        try:
            page = urlopen(req)
            html = page.read().decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")

            race = soup.find('h2', class_='premain-first-container-title')['title']
            times = soup.find_all('span', class_='race-date-js')

            # wec removes times from completed races
            if len(times) > 1:
                time = int(times[-2]['data-timestamp'])

                dt = datetime.fromtimestamp(time).astimezone(TIME_ZONE)
                races.append(Race(race, series, dt, 'Max'))
        except HTTPError:
            break

        index += 1

    return races


def process_nascar_nationals() -> list:
    """Fetch official national NASCAR series' schedules from NASCAR.com."""
    page = urlopen(f'https://cf.nascar.com/cacher/{datetime.now().year}/race_list_basic.json')
    data = json.load(page)

    races = []
    for s in data:
        if s == 'series_1':
            series = Series('NCS', 'https://www.espn.com/racing/schedule', ['NASCAR', 'Stock', 'Premier'])
        elif s == 'series_2':
            series = Series('NXS', 'https://www.espn.com/racing/schedule/_/series/xfinity', ['NASCAR', 'Stock'])
        elif s == 'series_3':
            series = Series('NCTS', 'https://www.espn.com/racing/schedule/_/series/camping', ['NASCAR', 'Stock'])
        else:
            continue

        def fromisoformat(date: str):
            return datetime.fromisoformat(date).replace(tzinfo=tz.gettz('America/New_York')).astimezone(TIME_ZONE)

        races += [Race(r['race_name'], series, fromisoformat(r['race_date']), r['television_broadcaster']) for r in data[s]]

    return races


if __name__ == '__main__':
    # build a list of races from each series
    races = []
    for l in series:
        try:
            l.generate_races()
            races.extend(l.races)
        except HTTPError:
            print(f'Unable to fetch {l.name}')

    races += process_nascar_nationals()

    # sort the races by time
    races.sort(key=lambda r: r.time)

    # pull content from data/ files to prepend
    prepend = ''
    for file in glob.glob('data/*.csv'):
        prepend += open(file, 'r').read()
        if not prepend.endswith('\n'):
            prepend += '\n'

    # write the races to CSV file
    with open('races.csv', 'w') as f:
        f.write(prepend)
        f.write('\n'.join([r.build_row() for r in races]))
