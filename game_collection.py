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

class Collection(object):

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
        
        # for each date, store the list of (game, event) pairs
        self.datestore = defaultdict(list)

        # also for each date, store how many games we had on that day
        self.datecounts = defaultdict(int)

        # for each game, store its info
        self.gamestore = {}

        # keep track of the last day on which we acquired a game
        self.last_acquired = None

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

            # add the game and event to our datestore
            self.datestore[date].append((gameobj, event))

            # modify the game object with our event
            if event == Event.GET:
                gameobj.get = date
            elif event == Event.PLAY:
                gameobj.play = date
            else:
                raise ValueError(
                    "game '{name}' has invalid event: '{event}'".format(
                        name=name, event=event))

        # get the count each day from START to TODAY
        current = START
        while current <= TODAY:
            # sum up our game events
            counter = 0
            for (_, event) in self.datestore[current]:
                if event == Event.GET:
                    counter += 1
                    # we acquired a game on this day
                    self.last_acquired = current
                elif event == Event.PLAY:
                    counter -= 1

            # also include yesterday's final count
            yesterday = current - datetime.timedelta(days=1)
            counter += self.datecounts[yesterday]

            # set today's count
            self.datecounts[current] = counter

            # move on to the next date
            current += datetime.timedelta(days=1)

    def count(self, date):
        """Count how many games we have on any given date"""
        return self.datecounts[date]

    def games_get(self, date):
        """List which games we got on a given date"""
        return [g for (g,e) in self.datestore[date] if e == Event.GET]

    def games_play(self, date):
        """List which games we played on a given date"""
        return [g for (g,e) in self.datestore[date] if e == Event.PLAY]

    def last_acquired_date(self):
        """Return the date on which we last acquired a game"""
        return self.last_acquired

    def tooltip(self, date):
        """Generate the line chart tooltip for a given date (using HTML)"""

        # let's make a list of lines, and then separate by <br> because html
        lines = []

        # get the day of week (full name)
        weekday = "<b>%s</b>" % date.strftime('%A')
        lines.append(weekday)

        # get the date as <abbv month> <day>, <year>
        datestr = "<b>%s</b>" % date.strftime('%b %d, %Y')
        lines.append(datestr)

        # get the game count
        countstr = "Game Count: <b>%s</b>" % self.count(date)
        lines.append(countstr)

        # put it all together
        multiline = "<br>".join(lines)

        # wrap it in a tooltip div for format funtimes
        div = '<div class="google-tooltip">%s</div>' % multiline

        # return it
        return div

    def get_unplayed(self):
        """Get a list of names of unplayed games"""

        return [g for g in self.gamestore if not self.gamestore[g].is_played()]
