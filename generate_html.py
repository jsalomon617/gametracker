#!/usr/bin/python

import datetime
import re

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

def get_template():
    """Return our template string, ready for formatting"""

    # first read in our template file
    with open("template.html") as f:
        content = f.read()

    # now find all of our format strings
    format = "{{ ([a-zA-Z0-9_]+?) }}"
    matches = re.findall(format, content)

    # now replace normal curly braces with double curly braces
    replacements = [
        ("{", "{{"),
        ("}", "}}"),
    ]
    replacements.extend([
        ("{{{{ %s }}}}" % m, "{%s}" % m) for m in matches
    ])
    for (old, new) in replacements:
        content = content.replace(old, new)

    return (content, matches)

def generate_webpage(collection):
    """Print our webpage"""

    ### extract the bits we care about from the collection
    # get the datatable blob
    datatable = chart_datatable(collection)

    # get the date data
    datedata = date_data(collection)

    # get the list of unplayed games
    unplayed = collection.get_unplayed()
    unplayed.sort()

    # get the date we last acquired a game
    last_acquired = collection.last_acquired_date()

    ### prepare them for formatting
    format = {
        "datedata": datedata,
        "datatable": datatable,
        "last_acquired": str(last_acquired),
        "js_last_acquired": date_js(last_acquired),
        "unplayed_count": len(unplayed),
        "unplayed_lines": "<br>".join(unplayed),
    }

    ### get the template data
    content, matches = get_template()

    ### confirm that our formatting blob is exactly correct
    if sorted(format.keys()) != sorted(matches):
        raise ValueError("invalid formatting blob!")

    ### go ahead and do the formatting
    page = content.format(**format)

    ### spit it out
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
