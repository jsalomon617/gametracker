#!/usr/bin/python

"""
Tracks game-breaker data - aka the series of records of "longest time since
getting a new game", and the games that broke the current chain each time.
"""

import datetime

from bgg_link import linked_name

class GameBreaker(object):

    def __init__(self, date, score, *games):
        self.date = date
        self.score = score
        self.games = games


# when we started this
GAMEBREAKER_START_DATE = datetime.date(2016, 12, 3)

# transcribe the original info from paper from before we had a tracker
_GAMEBREAKER_INPUT_DATA = [
    GameBreaker(datetime.date(2016, 12, 7), 4,
        linked_name("Carcassonne Catapult", [38855])),
    GameBreaker(datetime.date(2016, 12, 19), 10,
        linked_name("Nantucket", [182064])),
    GameBreaker(datetime.date(2017, 1, 8), 20,
        linked_name("Shadows over Camelot: The Card Game", [129904]),
        linked_name("Ticket to Ride", [9209]),
        linked_name("Star Realms", [147020])),
    GameBreaker(datetime.date(2017, 3, 17), 21,
        linked_name("Saga of the Northmen", [177248])),
    GameBreaker(datetime.date(2017, 5, 30), 30,
        linked_name("BSG: Daybreak Expansion", [141648])),
]

