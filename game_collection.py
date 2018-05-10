#!/usr/bin/python

from collections import defaultdict
import datetime

# start of our tracker
START = datetime.date(2017, 07, 30)

# today's date
TODAY = datetime.date.today()

class Event:
    """We either get games or play them"""
    GET = 1
    PLAY = 2


class Game(object):
    """Stores relevant info about a specific game"""

    def __init__(self, name):
        # store our initial info about the game
        self.name = name

        # store other things we may learn later
        self.get = None
        self.play = None

    def is_owned(self):
        """Whether or not we acquired the game (should always be true, logically)"""
        return self.get is not None

    def is_played(self):
        """Whether or not we've played the game yet"""
        return self.play is not None


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
        return [g for (g,e) in self.events if e == Event.PLAY]


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

        datestr, eventstr, name = line.split(None, 2)

        # parse the date properly
        date = datetime.datetime.strptime(datestr, "%Y-%m-%d").date()

        # parse the event into an enum
        event = eventmap[eventstr]

        # return our data
        return name, date, event

    def wipe(self):
        """Wipe our stored data (also useful for initializing)"""

        # for each game, store its object (keyed by name)
        self.gamestore = {}

        # for each date, store its object (keyed by datetime.date object)
        self.datestore = {}

        # keep track of the last day on which we acquired a game
        self.last_acquired = None

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
        for line in lines:
            # parse the line
            name, date, event = self.parse_line(line)
            
            # get the game object (creating it if necessary)
            if name not in self.gamestore:
                self.gamestore[name] = Game(name)
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
            date_current.stats["count"] = date_previous.stats["count"] + date_current.net

            ### update last acquired day if necessary
            if date_current.acquired:
                self.last_acquired = current

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
        netweek = "7-Day Rolling Net: <b>%s</b>" % delta_prefix(self.net_week(date))
        lines.append(netweek)

        # put it all together
        multiline = "<br>".join(lines)

        # wrap it in a tooltip div for format funtimes
        div = '<div class="google-tooltip">%s</div>' % multiline

        # return it
        return div

    def get_unplayed(self):
        """Get a list of names of unplayed games"""

        return [g for g in self.gamestore if not self.gamestore[g].is_played()]
