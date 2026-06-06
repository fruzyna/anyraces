from datetime import datetime, timezone
from dateutil import tz
from json import load
from pathlib import Path
from glob import glob

YEAR = datetime.now().year


class AnyRaces(object):
    """Primary configuration handling object."""

    CONFIG_FILE = Path('config/anyraces.json')

    def __init__(self):
        self.manual_dir = Path('data')
        self.race_cache = Path('races.csv')
        self.time_zone = tz.gettz('America/Chicago')
        self.series = []
        self.streams = []

    def read_config(self):
        """Reads in the default configuration file config/anyraces.json."""
        if not AnyRaces.CONFIG_FILE.exists():
            print('Could not find config file', AnyRaces.CONFIG_FILE)
            return

        with open(AnyRaces.CONFIG_FILE, 'r') as f:
            config = load(f)
            self.manual_dir = Path(config['manual_entries_dir'])
            self.race_cache = Path(config['race_cache_file'])
            self.time_zone = tz.gettz(config['time_zone'])
            self.streams = config['streams']
            self.series = {key:Series(s) for key, s in config['series'].items() if s['enabled']}

    def read_manual_entries(self):
        """Reads in races from all CSV files in the manual_entries_dir."""
        races = []
        for file in glob(f'{self.manual_dir}/*.csv'):
            races += [Race.from_row(l.strip(), self.time_zone) for l in open(file, 'r').readlines() if l.strip()]

        print('Read', len(races), 'manually entered races')
        return races

    def read_races(self):
        """Reads in races from the race_cache_file."""
        races = []
        if self.race_cache.exists():
            with open(self.race_cache, 'r') as f:
                races = [Race.from_row(r, self.time_zone) for r in f.readlines() if ',' in r]

        print('Read', len(races), 'cached races')
        return races

    def write_races(self, races: list['Race']):
        """Writes a given set of races to the race_cache_file."""
        with open(self.race_cache, 'w') as f:
            f.write('\n'.join([r.build_csv_row(self) for r in races]))


class Series(object):
    """Represents metadata of a single racing series."""

    def __init__(self, series: object):
        self.name = series['name']
        self.schedule_url = series['source'].replace('YEAR', str(YEAR))
        self.tags = series['tags']


class Race(object):
    """Represents a single scheduled race."""

    def __init__(self, name: str, series: str, time: datetime, channel: str):
        self.name = name.replace('’', "'").replace(',', '')
        self.time = time
        self.channel = channel.replace(' ', '')
        self.series = series
    
    @staticmethod
    def from_row(row, time_zone: timezone):
        """Alternative to the constructor, provide a single CSV row representing the race and the timezone to assume."""
        values = row.split(',')
        name = values[0]
        series = values[1]
        date = values[2]
        time = values[3]
        channel = values[4]
        dt = datetime.strptime(f'{YEAR}/{date} {time}', '%Y/%m/%d %H:%M').replace(tzinfo=time_zone)
        return Race(name, series, dt, channel)

    def build_csv_row(self, ar: AnyRaces):
        """Builds a CSV row of data from the race."""
        tags = ' '.join(ar.series[self.series].tags)
        date = self.time.strftime('%m/%d')
        time = self.time.strftime('%H:%M')
        return ','.join([self.name, self.series, date, time, self.channel, tags])

    def build_html_row(self, ar: AnyRaces):
        """Builds an HTML table-row for the race."""
        channel = ' '.join([f'<a target="_blank" class="{ch.replace("?", "").lower()}" href="{ar.streams[ch] if ch in ar.streams else ""}">{ch}</a>' for ch in self.channel.split(' ')])
        title = ar.series[self.series].name if self.series in ar.series else ''
        return f'<tr class="row {ar.series[self.series].tags}"><td class="race">{self.name}</td><td class="series {self.series}" title="{title}">{self.series}</td><td class="date">{self.time.strftime("%m/%d")}</td><td class="time">{self.time.strftime("%H:%M")}</td><td class="channel">{channel}</td></tr>'

    def __eq__(self, race):
        """Ony compare races by series and name. Overlaps do happen in some series."""
        return self.name == race.name and self.series == race.series and self.time.month == race.time.month
