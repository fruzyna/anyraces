from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import glob


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
    Series('NCS', 'https://www.espn.com/racing/schedule', ['NASCAR', 'Stock', 'Premier']),
    Series('NXS', 'https://www.espn.com/racing/schedule/_/series/xfinity', ['NASCAR', 'Stock']),
    Series('NCTS', 'https://www.espn.com/racing/schedule/_/series/camping', ['NASCAR', 'Stock']),
    Series('ARCA', 'https://www.arcaracing.com/2024-race-broadcast-schedule/', ['Stock']),
    Series('INDY', 'https://www.espn.com/racing/schedule/_/series/indycar', ['IndyCar', 'Open-Wheel', 'Premier']),
    Series('NXT', 'https://www.indycar.com/INDYNXT/Schedule', ['IndyCar', 'Open-Wheel']),
    #Series('F1', 'https://www.espn.com/f1/schedule', ['Grand-Prix', 'Open-Wheel', 'Premier']),
    Series('F1', 'https://www.espn.com/racing/schedule/_/series/f1', ['Grand-Prix', 'Open-Wheel', 'Premier']),
    Series('WTSC', 'https://www.imsa.com/weathertech/tv-streaming-schedule/', ['IMSA', 'GT', 'Prototype', 'Premier']),
    Series('PILOT', 'https://www.imsa.com/michelinpilotchallenge/tv-streaming-schedule/', ['IMSA', 'GT', 'Touring'])
]

YEAR = now = datetime.now().year


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
            date = date.replace('Noon', '12:00 PM')
            if date != 'DATE':
                # use noon if time is not yet set
                if date.endswith('TBD'):
                    date = date.replace('TBD', '12:00 PM ET')

                dt = datetime.strptime(f'{YEAR} {date.replace(".", "")}', '%Y %a, %b %d %I:%M %p ET')

                # use track as race name
                race = ''
                skip = False
                for s in cells[1].strings:
                    if not race:
                        race = s
                    # interpret postponed dates
                    elif s.startswith("**Race postponed to "):
                        date = s[s.index(' to ')+4:]
                        dt = datetime.strptime(f'{YEAR} {date}', '%Y %B %d at %I:%M %p')
                    elif 'Practice' in s or 'Qualifying' in s or 'Shootout' in s:
                        skip = True
                    elif 'Sprint' in s:
                        race += ' (Sprint)'

                # remove an hour for central time
                dt = dt - timedelta(hours=1)

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
    rows.pop(0)

    for row in rows:
        cells = row.find_all("td")
        # interpret date time
        date = cells[2].string
        if " - " in date:
            dt = datetime.strptime(f'{YEAR} {date}', '%Y %b %d - %I:%M %p')
            dt = dt - timedelta(hours=1)

            # interpret race name
            race = ''
            for s in cells[1].strings:
                if not race:
                    race = s

            tv = cells[3].string
            if tv is None:
                tv = 'ESPN?'

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
        name = row.find('a', class_='onTv-event-title').string.strip()
        name = name.replace(' (Only Available To Stream In The United States On Peacock Premium)', '')
        name = name.replace(' (Available Globally)', '')
        date = row.find("span", class_='date-display-single').string.split(' -')[0]
        dt = datetime.strptime(date, '%A, %B %d, %Y – %I:%M %p')
        dt = dt - timedelta(hours=1)

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
        date = item.find("div", class_='schedule-list__date')
        month = date.contents[0].strip()
        day = date.find('span', class_='schedule-list__date-day').string.strip()
        time = item.find('span', class_='timeEst').string.replace('ET', '').strip()
        # use noon if time is not yet set
        if time == 'TBD':
            dt = datetime.strptime(f"{month} {day} {YEAR} 12:00 PM", '%b %d %Y %I:%M %p')
        else:
            dt = datetime.strptime(f"{month} {day} {YEAR} {time}", '%b %d %Y %I:%M %p')

        dt = dt - timedelta(hours=1)

        # determine TV channel by image
        tvimg = item.find("div", class_='schedule-list__broadcast-logos').a['href'].upper()
        if 'PEACOCKTV' in tvimg:
            tv = 'Peacock'
        elif 'NBCSPORTS' in tvimg:
            tv = 'NBC'
        elif 'USANETWORK' in tvimg:
            tv = 'USA'
        else:
            tv = 'Unknown'

        # combine into EventBot compatible dictionary
        races.append(Race(name, series, dt, tv))

    return races


def process_arca(url: str, series: Series) -> list:
    """Fetch race schedule from espn.com/racing"""
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
            if time == 'TBA':
                time = '12:00 pm ET'

            if ':' not in time:
                time = time.replace(' p.m.', ':00 pm')

            date = f'{date} {time}'.replace('.', '')
            try:
                dt = datetime.strptime(f'{YEAR} {date}', '%Y %A, %b %d %I:%M %p ET')
            except ValueError:
                dt = datetime.strptime(f'{YEAR} {date}', '%Y %A, %B %d %I:%M %p ET')

            # remove an hour for central time
            dt = dt - timedelta(hours=1)

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


if __name__ == '__main__':
    # build a list of races from each series
    races = []
    for l in series:
        l.generate_races()
        races.extend(l.races)

    # sort the races by time
    races.sort(key=lambda r: r.time)

    # pull content from data/ files to prepend
    prepend = ''
    for file in glob.glob('data/*.csv'):
        prepend += open(file, 'r').read() + '\n'

    # write the races to CSV file
    with open('races.csv', 'w') as f:
        f.write(prepend)
        f.write('\n'.join([r.build_row() for r in races]))
