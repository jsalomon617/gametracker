#!/usr/bin/python

from collections import defaultdict
import datetime

# start of our tracker
START = datetime.date(2017, 07, 30)

# today's date
TODAY = datetime.date.today()

class Event:
    GET = 1
    PLAY = 2

class Game(object):

    def __init__(self, name):
        # store our initial info about the game
        self.name = name

        # store other things we may learn later
        self.get = None
        self.play = None

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
            gameobj = self.gamestore.get(name, Game(name))

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

    def chart_datatable(self, start=None, end=None):
        """Given a start and end date (inclusive), get the data set of game counts
        per day to send to google charts.  By default, start will be our global start, and
        end will be today."""
        
        if start is None:
            start = START
        if end is None:
            end = TODAY

        lines = []
        while start <= end:
            # format the date nicely
            datestr = "new Date({year}, {month}, {day})".format(
                year=start.year, month=start.month - 1, day=start.day)
            gamecount = self.count(start)
            lines.append("[{date}, {count}]".format(date=datestr, count=gamecount))
            
            # increment the date
            start += datetime.timedelta(days=1)

        # put the blob together
        dataset = ",\n".join(lines)

        # return it
        return dataset


def generate_webpage(datatable):
    """Print our webpage"""

    # start with blank page
    page = ""

    # create our magical string of bullshit
    content = """
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js">
    </script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['line']});
      google.charts.setOnLoadCallback(drawChart);

      function drawChart() {

        var chartDiv = document.getElementById('chart_div');

        var data = new google.visualization.DataTable();
        data.addColumn('date', 'Date');
        data.addColumn('number', 'Game Count');
        data.addRows([
        %s
        ]);

        var options = {
          chart: {
            title: 'Game Counts'
          },
          width: 900,
          height: 500
        };

        var chart = new google.charts.Line(chartDiv);
        chart.draw(data, options);
      }
    </script>
    <div id="chart_div"></div>

    </body>
    """

    # go ahead and format it
    content %= datatable

    # actually add it
    page += content

    # spit it out
    return page

def main():
    """Do the actual stuff"""
    
    # create our collection
    collection = Collection()
    
    # get the datatable blob
    datatable = collection.chart_datatable()

    # get the page
    page = generate_webpage(datatable)

    # write it to file
    with open("index.html", "w") as f:
        f.write(page)

# actually do shit
if __name__ == "__main__":
    main()
