#!/usr/bin/python

import datetime

from game_collection import START, TODAY, Collection


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

def chart_datatable(collection, start=None, end=None):
    """Get the dataset of game counts per day for the Google LineChart."""

    # get our row function
    def f(date):
        # format the date nicely
        datestr = date_js(date)

        # get the other data
        gamecount = collection.count(date)
        tooltip = collection.tooltip(date)

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


def escape(txt):
    """Given some text, escape it to make it JavaScript-safe"""

    replacements = [
        ("'", "\\'"),
    ]

    for (old, new) in replacements:
        txt = txt.replace(old, new)

    return txt

def generate_webpage(collection):
    """Print our webpage"""

    # get the datatable blob
    datatable = chart_datatable(collection)

    # get the date data
    datedata = date_data(collection)

    # get the list of unplayed games
    unplayed = collection.get_unplayed()
    unplayed.sort()

    # get the date we last acquired a game
    last_acquired = collection.last_acquired_date()

    # get the average of daily and weekly nets
    average_net_day = collection.average_net_day()
    average_net_week = collection.average_net_week()



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
          //toggleButton();
        });

        // show permanent game info when we click a specific day
        google.visualization.events.addListener(chart, 'select', function () {
          //toggleButton();
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
    <br>
    Average Daily Net Change: <b>%s</b>
    <br>
    Average 7-Day Rolling Net Change: <b>%s</b>
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
        "%.2f" % average_net_day,
        "%.2f" % average_net_week,
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
    
    # get the page
    page = generate_webpage(collection)

    # write it to file
    with open("www/index.html", "w") as f:
        f.write(page)

# actually do shit
if __name__ == "__main__":
    main()
