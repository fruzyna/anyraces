from datetime import datetime, timedelta


DICTIONARY = {
    'NCS': 'NASCAR Cup Series',
    'NXS': 'NASCAR Xfinity Series',
    'NCTS': 'NASCAR Craftsman Truck Series',
    'ARCA': 'ARCA Menards Series',
    'INDY': 'NTT IndyCar Series',
    'NXT': 'Indy NXT Series',
    'F1': 'Formula One',
    'WTSC': 'IMSA WeatherTech SportsCar Championship',
    'PILOT': 'IMSA Michelin Pilot Challenge'
}


class Race(object):

    def __init__(self, values: list):
        self.name = values[0]
        self.series = values[1]
        self.date = values[2]
        self.time = values[3]
        self.channel = values[4]
        self.tags = values[5]

    def build_row(self, class_name: str) -> str:
        """Builds an HTML table-row for the race. An additional classname can be pased in."""
        channel = ' '.join([f'<span class="{ch.replace("?", "")}">{ch}</span>' for ch in self.channel.split(' ')])
        title = DICTIONARY[self.series] if self.series in DICTIONARY else ''
        return f'<tr class="row {self.tags} {class_name}"><td class="race">{self.name}</td><td class="series {self.series}" title="{title}">{self.series}</td><td class="date">{self.date}</td><td class="time">{self.time}</td><td class="channel">{channel}</td></tr>'

    @property
    def datetime(self) -> datetime:
        """Convert the date and time to a Python datetime."""
        now = datetime.now()
        return datetime.strptime(f'{now.year}/{self.date} {self.time}', '%Y/%m/%d %H:%M')


def build_link(name: str, href: str):
    """Builds an HTML link to a given URL."""
    return f'<a href="{href}">{name}</a>'


def build_tag(tag: str, query='tag') -> str:
    """Builds an HTML link to query a given tag."""
    title = DICTIONARY[tag] if tag in DICTIONARY else ''
    return f'<a href="?{query}={tag}" title="{title}">{tag}</a>'


def generate_document(file: str, title: str, races: list, tags: list, series: list):
    """Generates an HTML document from a list of races."""
    # convert the list of races to a HTML string of table-rows
    rows = '\n'.join([r.build_row('gray' if i % 2 == 0 else '') for i, r in enumerate(races)])

    with open(file, 'w') as f:
        f.write(f'<html><head><title>Any Races This {title}?</title><link rel="stylesheet" type="text/css" href="style.css"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0"></head><body>')
        f.write(f'<h1>Any <span id="tag"></span>Races This {title}?</h1>')

        # add a row of date range links
        f.write(f'<div class="links">{build_link("This Week", "/week.html")}{build_link("This Month", "/month.html")}{build_link("This Year", "/")}</div>')

        # add a row of series links
        series = ''.join([build_tag(l, 'series') for l in series])
        f.write(f'<div class="links">{series}</div>')

        # add a row of tag links
        tags = ''.join([build_tag(t) for t in tags])
        f.write(f'<div class="links">{tags}</div>')

        # build the main table
        f.write(f'<div id="disclaimer">All times are US Central Time</div>')
        f.write(f'<table><tr><th>Race</th><th>Series</th><th>Date</th><th>Time</th><th>Channel</th></tr>{rows}</table>')

        # add some note to the bottom of the page
        f.write('<div id="notes">Data sourced from ESPN, Indycar, IMSA, and ARCA<br>')
        f.write(f'Updated every Tuesday, last updated {datetime.now().strftime("%m/%d %H:%M")}<br>')
        f.write('<a href="https://github.com/fruzyna/anyraces">Open Source on Github</a></div>')

        # load the JS last so it can access the table
        f.write('</body><script src="script.js"></script></html>')


if __name__ == '__main__':
    # read in the CSV file of races
    with open('races.csv', 'r') as f:
        races = [Race(r.split(',')) for r in f.readlines()]

    # filter the races date
    now = datetime.now()
    this_week = list(filter(lambda r: r.datetime > now and r.datetime < now + timedelta(weeks=1), races))
    this_month = list(filter(lambda r: r.datetime > now and r.datetime < now + timedelta(weeks=5), races))

    # find all unique tags and series in the races
    tags = []
    series = []
    for race in races:
        if race.series not in series:
            series.append(race.series)

        for tag in race.tags.strip().split(' '):
            if tag not in tags:
                tags.append(tag)

    # sort tags alphabetically
    tags.sort()
    series.sort()

    # generate each HTML document
    generate_document('index.html', 'Year', races, tags, series)
    generate_document('week.html', 'Week', this_week, tags, series)
    generate_document('month.html', 'Month', this_month, tags, series)
