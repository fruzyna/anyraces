from datetime import datetime, timedelta
from os.path import exists


RACES_FILE = 'races.csv'
MANUAL_FILE = 'manual.csv'

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

HEADERS = """<link rel="stylesheet" type="text/css" href="style.css">
             <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
             <meta http-equiv="Content-Type" content="text/html; charset=utf-8">"""
DISCLAIMER = '<div id="disclaimer">All times are US Central Time</div>'
TABLE_HEADER = '<tr><th>Race</th><th>Series</th><th>Date</th><th>Time</th><th>Channel</th></tr>'
LINKS = '<div class="links"><a href="/Week.html">This Week</a><a href="/Month.html">This Month</a><a href="/Year.html">This Year</a></div>'
NOTES = f"""<div id="notes">Data sourced from ESPN, Indycar, IMSA, and ARCA<br>
                           Updated every Tuesday, last updated {datetime.now().strftime("%m/%d %H:%M")}<br>
                           <a href="https://github.com/fruzyna/anyraces">Open Source on Github</a></div>"""
FOOTERS = '<script src="script.js"></script>'

YEAR = now = datetime.now().year


class Race(object):

    def __init__(self, values: list):
        self.name = values[0]
        self.series = values[1]
        self.date = values[2]
        self.time = values[3]
        self.channel = values[4]
        self.tags = values[5]
        self.datetime = datetime.strptime(f'{YEAR}/{self.date} {self.time}', '%Y/%m/%d %H:%M')

    def build_row(self) -> str:
        """Builds an HTML table-row for the race. An additional classname can be pased in."""
        channel = ' '.join([f'<span class="{ch.replace("?", "")}">{ch}</span>' for ch in self.channel.split(' ')])
        title = DICTIONARY[self.series] if self.series in DICTIONARY else ''
        return f'<tr class="row {self.tags}"><td class="race">{self.name}</td><td class="series {self.series}" title="{title}">{self.series}</td><td class="date">{self.date}</td><td class="time">{self.time}</td><td class="channel">{channel}</td></tr>'


def build_tag(span: str, tag: str) -> str:
    """Builds an HTML link to query a given tag."""
    title = DICTIONARY[tag] if tag in DICTIONARY else ''
    return f'<a href="/{tag}-{span}.html" title="{title}">{tag}</a>'


def generate_document(file: str, span: str, races: list, tags: str, series: str, tag=''):
    """Generates an HTML document from a list of races."""
    # convert the list of races to a HTML string of table-rows
    rows = '\n'.join([r.build_row() for r in races])
    if tag:
        tag += ' '

    title = f'Any {tag}Races This {span}?'

    with open(file, 'w') as f:
        f.write(f'<html><head><title>{title}</title>{HEADERS}</head><body>')
        f.write(f'<h1>{title}</h1>')

        # add a row of date range links
        f.write(LINKS)

        # add a row of series and tag links
        f.write(series)
        f.write(tags)

        # build the main table
        f.write(DISCLAIMER)
        f.write(f'<table>{TABLE_HEADER}{rows}</table>')

        # add some notes to the bottom of the page
        f.write(NOTES)

        # load the JS last so it can access the table
        f.write(f'</body>{FOOTERS}</html>')


if __name__ == '__main__':
    # read in the CSV file of races
    with open(RACES_FILE, 'r') as f:
        races = [Race(r.split(',')) for r in f.readlines()]

    # read in an optional additional CSV file of manually added races
    if exists(MANUAL_FILE):    
        with open(MANUAL_FILE, 'r') as f:
            races += [Race(r.split(',')) for r in f.readlines()]

    # sort the races by time
    races.sort(key=lambda r: r.datetime)

    # filter the races date
    now = datetime.now()
    this_month = list(filter(lambda r: r.datetime > now and r.datetime < now + timedelta(weeks=5), races))
    this_week = list(filter(lambda r: r.datetime < now + timedelta(weeks=1), this_month))

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

    # add a row of series and tag links
    series_week = f'<div class="links">{"".join([build_tag("Week", l) for l in series])}</div>'
    tags_week = f'<div class="links">{"".join([build_tag("Week", t) for t in tags])}</div>'
    series_month = f'<div class="links">{"".join([build_tag("Month", l) for l in series])}</div>'
    tags_month = f'<div class="links">{"".join([build_tag("Month", t) for t in tags])}</div>'
    series_year = f'<div class="links">{"".join([build_tag("Year", l) for l in series])}</div>'
    tags_year = f'<div class="links">{"".join([build_tag("Year", t) for t in tags])}</div>'

    # generate each HTML document
    generate_document('Year.html', 'Year', races, tags_year, series_year)
    generate_document('Week.html', 'Week', this_week, tags_week, series_week)
    generate_document('Month.html', 'Month', this_month, tags_month, series_month)

    for s in series:
        filt = lambda r: r.series == s
        series_str = f'<div class="links">{"".join([build_tag(s, l) for l in series])}</div>'
        tags_str = f'<div class="links">{"".join([build_tag(s, t) for t in tags])}</div>'
        generate_document(f'{s}-Year.html', 'Year', list(filter(filt, races)), tags_year, series_year, s)
        generate_document(f'{s}-Week.html', 'Week', list(filter(filt, this_week)), tags_week, series_week, s)
        generate_document(f'{s}-Month.html', 'Month', list(filter(filt, this_month)), tags_month, series_month, s)

    for tag in tags:
        filt = lambda r: tag in r.tags
        series_str = f'<div class="links">{"".join([build_tag(tag, l) for l in series])}</div>'
        tags_str = f'<div class="links">{"".join([build_tag(tag, t) for t in tags])}</div>'
        generate_document(f'{tag}-Year.html', 'Year', list(filter(filt, races)), tags_year, series_year, tag)
        generate_document(f'{tag}-Week.html', 'Week', list(filter(filt, this_week)), tags_week, series_week, tag)
        generate_document(f'{tag}-Month.html', 'Month', list(filter(filt, this_month)), tags_month, series_month, tag)
