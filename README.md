Basic script to keep track of games acquired/played.  To set up, symlink the
www directory here to /var/www/{something} on your machine.

Additionally, run ./copy_hooks.sh - this script will copy our custom git hook(s)
(stored in source control) into Git's actual hooks directory (which is not actually
covered by normal source control).

Running ./generate_html.py will update www/index.html, which contains the relevant
game data.  There is a git hook set up to ensure that this script is run right before
a commit is made to the repo - this ensures that any changes made to the code or datafile
(which presumably were made if you're trying to commit) are also applied to the html file
(both to update it for viewers, and to make sure that it's updated as part of the commit).

TODO:

(*) Use BGG links instead of text names for games (find old games owned code, somehow
incorporate it here)

(*) Show "days since last game" value

(*) Show games acquired/played on any given day

(*) Show lifespan of a single game on request
