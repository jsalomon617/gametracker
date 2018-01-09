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

    def chart_datatable(self, start=None, end=None):
        """Get the dataset of game counts per day for the Google LineChart."""

        # get our row function
        def f(date):
            # format the date nicely
            datestr = date_js(date)

            # get the other data
            gamecount = self.count(date)
            tooltip = self.tooltip(date)

            # generate the row
            row = "[{date}, {count}, '{tooltip}']".format(
                date=datestr,
                count=gamecount,
                tooltip=tooltip
            )

            # return the row
            return row

        # get the actual datatable
        return date_array(f, start=start, end=end)

    def date_data(self, start=None, end=None):
        """Get a dataset showing games obtained and played each day"""

        def make_list(title, items):
            output = ""
            output += "<b>%s</b>" % title
            output += "<br>" + "<br>".join(items)
            return output

        # get our row function
        def f(date):
            # format the date nicely
            datestr = date_js(date)

            # get the count
            gamecount = self.count(date)

            # generate the get-list and play-list of each day
            gameinfo = []
            for (title, func) in (("Obtained", self.games_get), ("Played", self.games_play)):
                namelist = [escape(g.name) for g in func(date)]
                if len(namelist) == 0:
                    gameinfo.append("<b>No Games %s</b>" % title)
                else:
                    gameinfo.append(make_list("Games %s:" % title, namelist))
            gamestr = "<br>".join(gameinfo)

            # generate the row
            row = "[%s, %s, '%s']" % (datestr, gamecount, gamestr)
            return row

        # return the actual datatable
        return date_array(f, start=start, end=end)

    def get_unplayed(self):
        """Get a list of names of unplayed games"""

        return [g for g in self.gamestore if not self.gamestore[g].is_played()]

def date_js(obj):
    """Given a Python datetime object, convert it to a JavaScript 'new Date(...)'
    string"""

    datestr = "new Date({year}, {month}, {day})".format(
        year=obj.year, month=obj.month - 1, day=obj.day)
    return datestr

def date_array(f, start=None, end=None):
    """Generate a JavaScript array containing some kind of data, specified by
    our input function f.  Each row of the array will be for a specific day,
    ranging from start to end (inclusive).  By default, start will be our global
    start, and end will be today's date."""

    if start is None:
        start = START
    if end is None:
        end = TODAY

    lines = []
    while start <= end:
        # get the row from our function
        row = f(start)

        # add the row to our list of lines
        lines.append(row)

        # increment the date
        start += datetime.timedelta(days=1)

    # put the blob together
    dataset = "[%s]" % ",\n".join(lines)

    # return it
    return dataset

def escape(txt):
    """Given some text, escape it to make it JavaScript-safe"""

    replacements = [
        ("'", "\\'"),
    ]

    for (old, new) in replacements:
        txt = txt.replace(old, new)

    return txt

def generate_webpage(datatable, datedata, unplayed, last_acquired):
    """Print our webpage"""

    # start with blank page
    page = ""

    # create our magical string of bullshit
    content = """
    <html><head>

    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['corechart', 'line']});
      google.charts.setOnLoadCallback(drawChart);

      // get the dataset with game info for our sidebars
      var dataset = %s;

      function drawChart() {

        var data = new google.visualization.DataTable();
        data.addColumn('date', 'Date');
        data.addColumn('number', 'Game Count');
        data.addColumn({type: 'string', role: 'tooltip', p: {'html': true}});
        data.addRows(%s);

        var options = {
          vAxis: {
            title: 'Game Count',
            format: '#',
            gridlines: {count: -1},
          },
          hAxis: {
            title: 'Date',
            format: 'M/d/yy',
          },
          series: {
            1: {curveType: 'function'},
          },
          legend: {
            position: 'none',
          },
          tooltip: {
            trigger: 'both',
            isHtml: true,
          },
          title: 'Unplayed Game Counts',
          width: 900,
          height: 500
        };

        var chart = new google.visualization.LineChart(document.getElementById('chart_div'));

        // wait for the chart to finish drawing before calling the getImageURI() method
        google.visualization.events.addListener(chart, 'ready', function () {
          document.getElementById('png').innerHTML = '<img src="' + chart.getImageURI() + '">';
        });

        // show extra game information when we mouseover a specific day
        google.visualization.events.addListener(chart, 'onmouseover', function () {
          toggleButton();
        });

        // show permanent game info when we click a specific day
        google.visualization.events.addListener(chart, 'select', function () {
          toggleButton();
        });

        chart.draw(data, options);
      }
    </script>

    <script type="text/javascript">
      function toggleButton() {
        var button = document.getElementById('button');
        var div = document.getElementById('png');
        if (div.style.display !== 'none') {
          div.style.display = 'none';
          //button.innerHTML = 'Show Static Image';
        } else {
          div.style.display = 'block';
          //button.innerHTML = 'Hide Static Image';
        }
      };
    </script>

    <style>
      .google-tooltip {
        font-size: 15px;
        padding: 5px 5px 5px 5px;
        font-family: Arial, Helvetica;
      }
    </style>

    </head><body>

    <div id="chart_div"></div>

    Last Game Acquired on <b>%s</b>
    (<span id="dayDiff"></span> days ago)
    <br><br>

    <script>
        // count days since we last got a new game
        var last_acquired = %s;
        var today = new Date();
        today.setHours(0,0,0,0);
        var diff = Math.abs(today - last_acquired);
        var days = Math.floor(diff / (1000 * 60 * 60 * 24));

        // write the answer to our html
        var div = document.getElementById("dayDiff");
        div.textContent = days;
    </script>

    <button id='button' type='button' onclick='toggleButton()'>Toggle Static Image</button>

    <div id='png' style="display:none"></div>

    <br><br><br><img src="fine.png" />
    
    <br><br>
    <b><u>Unplayed Games (%s):</u></b>
    <br>
    %s

    </body></html>
    """

    # go ahead and format it
    unplayed_count = len(unplayed)
    unplayed_lines = "<br>".join(unplayed)
    content %= (
        datedata,
        datatable,
        str(last_acquired),
        date_js(last_acquired),
        unplayed_count,
        unplayed_lines,
    )

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

    # get the date data
    datedata = collection.date_data()

    # get the list of unplayed games
    unplayed = collection.get_unplayed()
    unplayed.sort()

    # get the date we last acquired a game
    last_acquired = collection.last_acquired_date()

    # get the page
    page = generate_webpage(
        datatable,
        datedata,
        unplayed,
        last_acquired,
    )

    # write it to file
    with open("www/index.html", "w") as f:
        f.write(page)

# actually do shit
if __name__ == "__main__":
    main()
