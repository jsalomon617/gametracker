#!/usr/bin/python

"""
Common library for turning game names and BGG IDs into links
"""

def linked_name(name, bgg_ids=None):
    """Return the name of the game as part of a BGG link, if possible"""

    # if we don't provide any bgg IDs, initialize to an empty list
    if bgg_ids is None:
        bgg_ids = []

    # the base bgg link
    base = "https://www.boardgamegeek.com/boardgame/{id}/"

    # check how many bgg IDs we have
    if len(bgg_ids) == 0:
        # we have no ID, just say so
        return "{name} (no BGG link)".format(name=name)
    elif len(bgg_ids) == 1:
        # we have exactly one ID, let's link the name
        link = base.format(id=bgg_ids[0])
        return "<a href={link} target=\\'_blank\\'>{name}</a>".format(link=link, name=name)
    else:
        # we have many ids, let's include them generically for now
        # TODO reference BGG library to provide names
        pairs = [(id, base.format(id=id)) for id in bgg_ids]
        return "{name} ({links})".format(
            name=name,
            links=", ".join([
                "<a href={link} target=\\'_blank\\'>{id}</a>".format(link=link, id=id)
                for (id, link) in pairs
            ])
        )

