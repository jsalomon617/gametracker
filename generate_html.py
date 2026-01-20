#!/usr/bin/python

import datetime
import re

from game_breaker import GAMEBREAKER_START_DATE
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
        games_gotten = self.games_get(date)
        games_played = self.games_play(date)
        for (title, game_sublist) in (("Obtained", games_gotten), ("Played", games_played)):
            namelist = [escape(g.name) for g in game_sublist]
            if len(namelist) == 0:
                gameinfo.append("<b>No Games %s</b>" % title)
            else:
                gameinfo.append(make_list("Games %s:" % title, namelist))
        gamestr = "<br>".join(gameinfo)

        # generate the row
        row = f"[{datestr}, {gamecount}, {len(games_gotten)}, {len(games_played)}]" #, '{gamestr}']"
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

def _table_row_for_unplayed_game(g):
    cells = [
        g.linked_name(),
        g.get,
    ]
    td_cells = [f'<td>{cell}</td>' for cell in cells]
    return f'<tr class="highlightedIfInDateRange">{"".join(td_cells)}</tr>'

def generate_webpage(collection):
    """Print our webpage"""

    ### extract the bits we care about from the collection
    # get the datatable blob
    datatable = chart_datatable(collection)

    # get the date data
    datedata = date_data(collection)

    # get the list of unplayed games (sorted by name-as-provided)
    unplayed = collection.get_unplayed()
    unplayed.sort(key=lambda g: g.name)

    # get the display links for the unplayed games + other metadata
    unplayed_rows = [
        _table_row_for_unplayed_game(g)
        for g in unplayed
    ]

    # get the date we last acquired a game
    last_acquired = collection.last_acquired_date()

    # get the last time that the count was lower than right now
    lowest_since = collection.lowest_since()

    # compute our gamebreakers
    game_breaker_start = GAMEBREAKER_START_DATE
    game_breaker_rows = "\n".join([
        '<tr><td>{score}</td><td>{date}</td><td style="text-align:left">{games}</td></tr>'.format(
            score=gb.score,
            date=str(gb.date),
            games="\n<br>".join(gb.games))
        for gb in collection.gamebreakers
    ])

    # get the info for our next gamebreaker
    next_game_breaker_date, next_game_breaker_count = collection.next_gamebreaker()

    # get stats by year and pretty-print them
    yearly_stats = collection.yearly_stats()
    years = [year for (year, _) in yearly_stats]
    stats = [stat for (stat, _) in yearly_stats[0][1]]

    yearly_stats_str = "\n".join([
        '<table>',
        '<tr><th rowspan="2">Stats</th><th colspan="{}">Yearly (Click Year to Set Range)</th><th>Selected Range</th></tr>'.format(len(years)),
        '<tr>{}</tr>'.format(''.join(
            [] #['<th></th>']
            + ['<th onclick="applyYear({year})" style="cursor: pointer;">{year}</th>'.format(year=h) for h in (years)]
            + ['<th><span id="start_date_str">2017-07-30</span> to <span id="end_date_str">Today</span></th>']
        )),
    ] + [
        '<tr>{}</tr>'.format(
            ''.join(
                ['<th>{}</th>'.format(stat)]
                + ['<td>{}</td>'.format(yearly_stats[i][1][j][1]) for i in range(len(years))]
                + ['<td><span id="variable_stats_{}"></span></td>'.format(stat.lower().replace(' ', '_'))]
            ))
        for (j, stat) in enumerate(stats)
    ] + [
        '</table>'
    ])

    # we explicitly define the min and max values of the chart, as multiples of 10 exclusive
    vertical_min = ((collection.lifetime_min() - 1) / 10) * 10
    vertical_max = (((collection.lifetime_max() + 1) / 10) + 1) * 10

    ### prepare them for formatting
    format = {
        "datedata": datedata,
        "datatable": datatable,
        "last_acquired": str(last_acquired),
        "js_last_acquired": date_js(last_acquired),
        "lowest_since": str(lowest_since),
        "unplayed_count": len(unplayed),
        "unplayed_lines": "\n".join(unplayed_rows),
        "game_breaker_start": str(game_breaker_start),
        "game_breaker_rows": game_breaker_rows,
        "next_game_breaker_date": str(next_game_breaker_date),
        "next_game_breaker_count": next_game_breaker_count,
        "yearly_stats": yearly_stats_str,
        "vertical_min": vertical_min,
        "vertical_max": vertical_max,
    }

    ### get the template data
    content, matches = get_template()

    ### confirm that our formatting blob is exactly correct
    if set(format.keys()) != set(matches):
        print(sorted(format.keys()))
        print(sorted(matches))
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
