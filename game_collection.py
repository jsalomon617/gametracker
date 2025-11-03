#!/usr/bin/python

from collections import defaultdict
import datetime

import bgg_link
from game_breaker import GameBreaker, _GAMEBREAKER_INPUT_DATA

# start of our tracker
START = datetime.date(2017, 7, 30)

# today's date
TODAY = datetime.date.today()

class Event:
    """We either get games or play them"""
    GET = 1
    PLAY = 2


class Game(object):
    """Stores relevant info about a specific game"""

    def __init__(self, name, bgg=None):
        # store our initial info about the game
        self.name = name

        # we may receive some BGG IDs with the game info; if so, store them
        self.bgg = [] if bgg is None else bgg

        # store other info we may get later
        self.get = None
        self.play = None

    def is_owned(self):
        """Whether or not we acquired the game (should always be true, logically)"""
        return self.get is not None

    def is_played(self):
        """Whether or not we've played the game yet"""
        return self.play is not None

    def linked_name(self, escape=False):
        """Return the name of the game as part of a BGG link, if possible"""

        return bgg_link.linked_name(self.name, self.bgg, escape=escape)


class Date(object):
    """Stores relevant info about a particular date"""

    def __init__(self, date):
        ### store the datetime date object
        self.date = date

        ### store other things we care about for later

        # list of (game, event) pairs that took place on this day
        self.events = []

        # net change in games today
        self.net = 0

        # did we acquire a game today?
        self.acquired = False

        # various stats we'll collate in the collection
        self.stats = {
            # count of total games owned on this date
            "count": 0,

            # net change in games in the last 7 days
            "net_week": 0,
        }

    def record_event(self, game, event):
        """Given a game and an event, record that they happened on this date"""

        # just append both things to our internal list
        self.events.append((game, event))

        # then modify our net
        if event == Event.GET:
            self.net += 1
            self.acquired = True
        elif event == Event.PLAY:
            self.net -= 1

    def games_get(self):
        """List the games we received today"""
        return [g for (g,e) in self.events if e == Event.GET]

    def games_play(self):
        """List the games we played today"""
        return [g for (g,e) in self.events if e == Event.PLAY]


class DateRange(object):
    """
    Stores relevant info about a range of dates

    We provide start and end (inclusive) datetime dates, but also
    the collection.  Because each game-Date object is the status as
    of the end of that day, we sometimes need the day before start.
    """

    def __init__(self, collection, start, end):
        # store our start/end datetimes and the collection
        self.collection = collection
        self.start = start
        self.end = end

    def stats(self):
        """ Return relevant stats for our range """

        # get the game-date objects for start (the day before) and end (the real day)
        bounded_start = self.start - datetime.timedelta(days=1)
        if not self.collection.has_date(bounded_start):
            bounded_start = self.start

        # counts at start and end
        start_count = self.collection.count(bounded_start)
        end_count = self.collection.count(self.end)

        # net change across the range, and formatted nicely
        net_change = end_count - start_count
        human_net = '+{}'.format(net_change) if net_change > 0 else str(net_change)

        # get total games acquired and played across the range
        acquired_count = 0
        played_count = 0
        index_date = self.start
        while index_date <= self.end:
            acquired_count += len(self.collection.games_get(index_date))
            played_count += len(self.collection.games_play(index_date))
            index_date += datetime.timedelta(days=1)

        # return our interesting stats
        return [
            ('Starting Count', start_count),
            ('Ending Count', end_count),
            ('Net Change', human_net),
            ('Games Acquired', acquired_count),
            ('Games Played', played_count),
        ]


class Collection(object):
    """Stores and compiles all of the relevant info about the collection"""

    DATA = "data.txt"

    def __init__(self):
        """Initialize our collection object"""

        # store the game data
        self.store()

    def read(self):
        """Read in our datafile, pass the sanitized set of lines"""
        with open(self.DATA) as f:
            data = f.read()
        lines = data.split("\n")
        lines = [x.strip() for x in lines]
        lines = [x for x in lines if x]
        return lines

    def parse_line(self, line):
        """Parse an individual line.  Current format expects:
        <date> <+ or -> <name>
        """

        eventmap = {
            "+": Event.GET,
            "-": Event.PLAY,
        }

        # split a fixed number of times on the default "any amount of whitespace" is silly
        datestr, eventstr, name = line.split(None, 2)

        # parse the date properly
        date = datetime.datetime.strptime(datestr, "%Y-%m-%d").date()

        # parse the event into an enum
        event = eventmap[eventstr]

        # if we're adding a game, we may have a BGG ID (but otherwise default
        # to nothing)
        bgg = None
        if event == Event.GET:
            # bgg IDs will always be at the very end
            pieces = name.rsplit(None, 1)

            # if there's only one piece, then it's a one-word name and clearly has no ID
            if len(pieces) == 2:
                start, end = pieces

                # ids should always start with "id" to really really minimize
                # accidental collisions
                if end.startswith("id"):
                    # strip that off
                    end = end[2:]

                    # ids will be comma-separated lists of values
                    ids = end.split(",")

                    # if they all match, store the list
                    if all([x.isdigit() and x[0] != "0" for x in ids]):
                        bgg = [int(x) for x in ids]
                        name = start

        # return our data
        return name, date, event, bgg

    def wipe(self):
        """Wipe our stored data (also useful for initializing)"""

        # for each game, store its object (keyed by name)
        self.gamestore = {}

        # for each date, store its object (keyed by datetime.date object)
        self.datestore = {}

        # keep track of the last day on which we acquired a game (init to our
        # start date, for simplicity)
        self.last_acquired = START

        # initialize our gamebreaker list
        self.gamebreakers = _GAMEBREAKER_INPUT_DATA[:]

        # clear our min and max
        self.count_min = None
        self.count_max = None

    def has_date(self, date):
        """Given a specific date, do we have it in the datestore?"""
        return date in self.datestore

    def get_date(self, date):
        """Given a specific date, get it from datestore (creating it if necessary)"""
        if date not in self.datestore:
            self.datestore[date] = Date(date)
        return self.datestore[date]

    def store(self):
        """Store the dataset by date and by name"""

        # reset the stored data
        self.wipe()

        # read our datafile
        lines = self.read()

        # go through each line
        last_date = None
        for line in lines:
            # parse the line
            name, date, event, bgg = self.parse_line(line)

            # enforce that our dates must be in order, for sanity
            if last_date is not None and date < last_date:
                raise ValueError(
                    "game {} has date {} older than last date {}".format(
                        name, date, last_date))
            last_date = date

            # get the game object (creating it if necessary)
            if name not in self.gamestore:
                # let's actually enforce that get events must come before play events
                if event == Event.PLAY:
                    raise ValueError("game %s on date %s has PLAY before GET" % (name, date))

                # if we haven't hit this, then clearly we're fine, and so can
                # also add the bgg ids
                self.gamestore[name] = Game(name, bgg=bgg)
            gameobj = self.gamestore[name]

            # modify the game object with our event
            if event == Event.GET:
                gameobj.get = date
            elif event == Event.PLAY:
                gameobj.play = date
            else:
                raise ValueError(
                    "game '{name}' has invalid event: '{event}'".format(
                        name=name, event=event))

            # add the game and event to our date object
            self.get_date(date).record_event(gameobj, event)


        # get the total count (and other fun stats) each day from START to TODAY
        # (most stats rely on previous days already having count defined)
        current = START
        while current <= TODAY:
            ### count of games on this day
            # get the date object for the current date and the previous date
            date_current = self.get_date(current)

            yesterday = current - datetime.timedelta(days=1)
            date_previous = self.get_date(yesterday)

            # yesterday's count should already be set, so just add today's net
            today_count = date_previous.stats["count"] + date_current.net
            date_current.stats["count"] = today_count

            ### update min and max if necessary
            if self.count_min is None or self.count_min > today_count:
                self.count_min = today_count
            if self.count_max is None or self.count_max < today_count:
                self.count_max = today_count

            ### store how long it's been since our last game, in case today is a gamebreaker
            days_since_last_game = current - self.last_acquired
            days_since_last_game = days_since_last_game.days

            ### update last acquired day if necessary
            if date_current.acquired:
                self.last_acquired = current

                # if this is a gamebreaker, add it to our list
                if days_since_last_game > self.gamebreakers[-1].score:
                    self.gamebreakers.append(GameBreaker(current, days_since_last_game,
                        *[g.linked_name() for g in date_current.games_get()]))

            ### net change in the last 7 days
            # get the date object from 7 days ago
            last_week = current - datetime.timedelta(days=7)
            date_last_week = self.get_date(last_week)

            # just subtract the counts
            date_current.stats["net_week"] = date_current.stats["count"] - date_last_week.stats["count"]

            ##########
            # at the end of the loop, increment the damn date
            ##########
            current += datetime.timedelta(days=1)

    def count(self, date):
        """Count how many games we have on any given date"""
        return self.get_date(date).stats["count"]

    def net(self, date):
        """Net change in games on a given date"""
        return self.get_date(date).net

    def net_week(self, date):
        """Net change in games in the week leading up to a given date"""
        return self.get_date(date).stats["net_week"]

    def games_get(self, date):
        """List which games we got on a given date"""
        return self.get_date(date).games_get()

    def games_play(self, date):
        """List which games we played on a given date"""
        return self.get_date(date).games_play()

    def last_acquired_date(self):
        """Return the date on which we last acquired a game"""
        return self.last_acquired

    def lowest_since(self, given_date=TODAY):
        """Return the most recent date with a lower playcount than the given date."""

        given_count = self.count(given_date)
        while given_date >= START:
            # get the count of games on the relevant date
            check_count = self.count(given_date)

            # if it's lower than our given count, stop now
            # "lowest since" actually does mean "find the last time it was strictly lower"
            if check_count < given_count:
                break

            # otherwise, go back a day
            given_date -= datetime.timedelta(days=1)

        # if we're here, we're either on the right date or went back through the entire
        # thing (at which point we call it good enough)
        return given_date

    def tooltip(self, date):
        """Generate the line chart tooltip for a given date (using HTML)"""

        def delta_prefix(val):
            """Given a value representing a change, return it as a string
            prefixed by + or - if it's nonzero"""

            if val > 0:
                return "+" + str(val)
            else:
                return str(val)

        # let's make a list of lines, and then separate by <br> because html
        lines = []

        # get the day of week (full name)
        weekday = "<b>%s</b>" % date.strftime('%A')
        lines.append(weekday)

        # get the date as <abbv month> <day>, <year>
        datestr = "<b>%s</b>" % date.strftime('%b %d, %Y')
        lines.append(datestr)

        # get the game count (and maybe the net, if relevant)
        countstr = "Game Count: <b>%s</b>" % self.count(date)
        net = self.net(date)
        if net != 0:
            countstr += " (%s)" % delta_prefix(net)
        lines.append(countstr)

        # get the rolling 7-day net
        #netweek = "7-Day Rolling Net: <b>%s</b>" % delta_prefix(self.net_week(date))
        #lines.append(netweek)

        # track actual changed games if details checkbox is checked
        changed_games = []
        for game in self.games_get(date):
            changed_games.append("+ %s" % game.linked_name(escape=True))
        for game in self.games_play(date):
            changed_games.append("- %s" % game.linked_name(escape=True))
        if changed_games:
            details_blob = "<br>".join(changed_games)
            details_div = '<div class="chart_details_div" style="display:none">%s</div>' % details_blob
            lines.append(details_div)

        # put it all together
        multiline = "<br>".join(lines)

        # wrap it in a tooltip div for format funtimes
        div = '<div class="google-tooltip">%s</div>' % multiline

        # return it
        return div

    def get_unplayed(self):
        """Get a list of unplayed game objects"""

        return [g for g in self.gamestore.values() if not g.is_played()]

    def next_gamebreaker(self):
        """Return the date and minimum score of the next possible gamebreaker"""

        # get the last gamebreaker's score
        gb = self.gamebreakers[-1]

        # add 1 to the score
        new_score = gb.score + 1

        # add that many days to last acquired
        new_date = self.last_acquired + datetime.timedelta(days=new_score)

        # return those
        return (new_date, new_score)

    def yearly_stats(self):
        """ Return the interesting stats per year """

        # get our relevant years
        start_year = START.year
        end_year = TODAY.year

        # be ready to track our stats objects
        stats_by_year = []

        # compute our stats per year
        for year in range(start_year, end_year+1):
            start_date = START + datetime.timedelta(days=1) if year == start_year else datetime.date(year, 1, 1)
            end_date = TODAY if year == end_year else datetime.date(year, 12, 31)
            year_range = DateRange(self, start_date, end_date)
            stats_by_year.append((year, year_range.stats()))

        # return the stats
        return stats_by_year

    def lifetime_min(self):
        """ Return lifetime min value """
        return self.count_min

    def lifetime_max(self):
        """ return lifetime max value """
        return self.count_max
