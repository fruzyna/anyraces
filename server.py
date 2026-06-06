from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from datetime import datetime, date, timedelta
from threading import Thread
from time import sleep

from races import YEAR, AnyRaces
from fetch import fetch_races, merge_races


class UpdateThread(Thread):
    """Thread used to periodically update the list of races."""

    def __init__(self):
        super().__init__()
        self.races = []
        self.last_update = datetime.now()

    def run(self):
        ar.read_config()
        old_races = ar.read_races()
        manual_races = ar.read_manual_entries()
        self.races = merge_races(old_races, manual_races)

        while True:
            races = fetch_races(ar)
            self.last_update = datetime.now()
            self.races = merge_races(self.races, races)
            ar.write_races(self.races)
            sleep(8 * 60 * 60)

    def wait_for_races(self):
        while not self.races:
            sleep(1)


def lookup_tag(tag: str):
    """Converts a series tag to the series name or returns the tag."""
    return ar.series[tag].name if tag in ar.series else tag


def build_tag(timeframe: str, tag: str) -> str:
    """Builds an HTML link to query a given tag."""
    return f'<a href="/?timeframe={timeframe}&tag={tag}" title="{lookup_tag(tag)}">{tag}</a>'


ar = AnyRaces()

thread = UpdateThread()
thread.start()
thread.wait_for_races()

app = FastAPI()


# build index to select line and stop
@app.get('/', response_class=HTMLResponse)
async def index(timeframe='', tag=''):
    # read in the CSV file of races
    races = thread.races

    # find all unique tags and series in the races
    tags = set()
    series = set()
    for race in races:
        series.add(race.series)

    for s in series:
        tags.update(ar.series[s].tags)

    series = list(series)
    series.sort()
    tags = list(tags)
    tags.sort()

    # filter by selected tag
    if tag:
        races = [r for r in races if r.series == tag or tag in ar.series[r.series].tags]

    # sort the races by time
    races.sort(key=lambda r: r.time)
    rangeTitle = 'this year'
    today = datetime(YEAR, date.today().month, date.today().day).replace(tzinfo=ar.time_zone)
    if timeframe == 'day':
        rangeTitle = 'today'
        races = [r for r in races if today < r.time < today + timedelta(days=1)]
    elif timeframe == 'month':
        rangeTitle = 'this month'
        races = [r for r in races if r.time.month == today.month]
    elif timeframe == 'year':
        races = [r for r in races if r.time.year == YEAR]
    else:
        rangeTitle = 'this week'
        races = [r for r in races if today < r.time < today + timedelta(days=7)]

    return f'<!DOCTYPE html>\
        <html>\
            <head>\
                <title>Any {tag}{' ' if tag else ''}races {rangeTitle}?</title>\
                <link rel="stylesheet" type="text/css" href="style.css">\
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">\
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">\
                <script src="script.js"></script>\
            </head>\
            <body>\
                <h1>Any <span id="timeframe">{lookup_tag(tag)}</span>{' ' if tag else ''}races <span id="timeframe">{rangeTitle}</span>?</h1>\
                <div class="links"><a href="/?timeframe=day">Today</a><a href="/?timeframe=week">This Week</a><a href="/?timeframe=month">This Month</a><a href="/?timeframe=year">This Year</a></div>\
                <div class="links">{"".join([build_tag(timeframe, s) for s in series])}</div>\
                <div class="links">{"".join([build_tag(timeframe, t) for t in tags])}</div>\
                <table>\
                    <tr><th>Race</th><th>Series</th><th>Date</th><th>Time</th><th>Channel</th></tr>\
                    {"\n".join([r.build_html_row(ar) for r in races])}\
                </table>\
                <div id="notes">\
                    <div id="disclaimer">All times central</div>\
                    Data sourced from ESPN, IndyCar, and NASCAR<br>\
                    Last updated {thread.last_update.strftime("%m/%d %H:%M")} UTC<br>\
                    <a href="https://github.com/fruzyna/anyraces">Open Source on Github</a>\
                </div>\
            </body>\
        </html>'


@app.get('/style.css', response_class=FileResponse)
async def styles():
    return 'style.css'


@app.get('/script.js', response_class=FileResponse)
async def styles():
    return 'script.js'
