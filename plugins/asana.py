#!/usr/bin/python3

import argparse
from collections import defaultdict
import datetime
import json
import os
import subprocess
import sys
import time

#import asana
#from asana.rest import ApiException


ASANA_SECRETS_FILE = "plugins/secrets/asana-secrets.json"
DATA_FILE = "data.txt"

PAT = "pat"
WORKSPACE_ID = "workspace_id"
PROJECT_ID = "project_id"


def quit():
    print()
    sys.exit(0)

def load_secrets():
    if not os.path.exists(ASANA_SECRETS_FILE):
        print("secrets file {} does not exist".format(ASANA_SECRETS_FILE))
        quit()

    with open(ASANA_SECRETS_FILE) as f:
        blob = f.read()
    try:
        data = json.loads(blob)
    except Exception as e:
        print("malformed secrets file {}".format(ASANA_SECRETS_FILE))
        print(e)
        quit()

    secrets = defaultdict(lambda: None)
    for key in data:
        if data[key]:
            secrets[key] = data[key]

    return secrets

"""
def to_capitalized_camelcase(snake_cased_words):
    return "".join([word.capitalize() for word in snake_cased_words.split("_")])

def get_x_factory(x):
    def get_x(api_client, *args):
        # may pass multiple arguments in, but it's always just what goes right to the list thing
        capitalized_camelcase_x = to_capitalized_camelcase(x)
        x_api_instance = getattr(asana, "{}Api".format(capitalized_camelcase_x))(api_client)
        try:
            api_response = getattr(x_api_instance, "get_{}".format(x))(*args)
            return [data for data in api_response]
        except ApiException as e:
            print("Exception when calling {}Api->get_{}: {}\n".format(capitalized_camelcase_x, x, e))
    return get_x

get_workspaces = get_x_factory("workspaces")
get_projects = get_x_factory("projects")
get_tasks = get_x_factory("tasks")
"""

WORKSPACES_CURL = """
curl --request GET \
     --url https://app.asana.com/api/1.0/workspaces \
     --header 'accept: application/json' \
     --header 'authorization: Bearer {pat}'
"""

PROJECTS_CURL = """
curl --request GET \
     --url 'https://app.asana.com/api/1.0/projects?workspace={workspace_id}' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer {pat}'
"""

TASKS_CURL = """
curl --request GET \
     --url 'https://app.asana.com/api/1.0/tasks?project={project_id}&opt_fields=name,completed' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer {pat}'
"""

def run_and_parse_curl(curl):
    return json.loads(subprocess.run(curl, shell=True, capture_output=True).stdout)["data"]

def get_workspaces(secrets):
    return run_and_parse_curl(WORKSPACES_CURL.format(pat=secrets[PAT]))

def get_projects(secrets):
    return run_and_parse_curl(PROJECTS_CURL.format(pat=secrets[PAT], workspace_id=secrets[WORKSPACE_ID]))

def get_tasks(secrets):
    return run_and_parse_curl(TASKS_CURL.format(pat=secrets[PAT], project_id=secrets[PROJECT_ID]))


# copied from game_collection.py
def parse_line(line):
    """Parse an individual line.  Current format expects:
    <date> <+ or -> <name>
    """

    # split a fixed number of times on the default "any amount of whitespace" is silly
    datestr, eventstr, name = line.split(None, 2)

    # parse the date properly
    date = datetime.datetime.strptime(datestr, "%Y-%m-%d").date()

    # if we're adding a game, we may have a BGG ID (but otherwise default
    # to nothing)
    bgg = None
    if eventstr == "+":
        # bgg IDs will always be at the very end
        pieces = name.rsplit(None, 1)

        # if there's only one piece, then it's a one-word name and clearly has no ID
        if len(pieces) == 2:
            start, end = pieces

            # ids should always start with "id" to really really minimize
            # accidental collisions
            if end.startswith("id"):
                # strip that off
                end = end[2:]

                # ids will be comma-separated lists of values
                ids = end.split(",")

                # if they all match, store the list
                if all([x.isdigit() and x[0] != "0" for x in ids]):
                    bgg = [int(x) for x in ids]
                    name = start

    name = name.strip()
    return name, date, eventstr, bgg


CREATE_TASK_CURL = """
curl --request POST \
     --url 'https://app.asana.com/api/1.0/tasks' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer %s' \
     --header 'content-type: application/json' \
     --data '
{
  "data": {
    "name": "%s",
    "html_notes": "<body>%s</body>",
    "projects": [
      "%s"
    ]
  }
}
'
"""

CREATE_COMPLETED_TASK_CURL = """
curl --request POST \
     --url 'https://app.asana.com/api/1.0/tasks' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer %s' \
     --header 'content-type: application/json' \
     --data '
{
  "data": {
    "completed": true,
    "name": "%s",
    "html_notes": "<body>%s</body>",
    "projects": [
      "%s"
    ]
  }
}
'
"""

COMPLETE_TASK_CURL = """
curl --request PUT \
     --url https://app.asana.com/api/1.0/tasks/%s \
     --header 'accept: application/json' \
     --header 'authorization: Bearer %s' \
     --header 'content-type: application/json' \
     --data '
{
  "data": {
    "completed": true
  }
}
'
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
        return "<a href=\\\"{link}\\\">{name}</a>".format(link=link, name=name)
    else:
        # we have many ids, let's include them generically for now
        # TODO reference BGG library to provide names
        pairs = [(id, base.format(id=id)) for id in bgg_ids]
        return "{name} ({links})".format(
            name=name,
            links=", ".join([
                "<a href=\\\"{link}\\\">{id}</a>".format(link=link, id=id)
                for (id, link) in pairs
            ])
        )



def update_tasks(secrets):
    # get existing tasks in the project
    tasks = get_tasks(secrets)
    tasks_by_name = {
        task["name"]: task
        for task in tasks
    }

    # walk through the data list
    game_data = []
    with open(DATA_FILE) as f:
        for line in f:
            game_data.append(parse_line(line))

    # possible actions are creating a new task, completing an existing task,
    # or creating a new task as completed (for backfilling)
    names_to_create = set()
    names_to_complete = set()
    names_to_create_as_completed = set()
    for (name, _, eventstr, _) in game_data:
        # if it's a create, we're trying to create the task
        if eventstr == "+" and name not in tasks_by_name:
            names_to_create.add(name)
        elif eventstr == "-" and name in tasks_by_name:
            names_to_complete.add(name)
        elif eventstr == "-" and name in names_to_create:
            names_to_create.remove(name)
            names_to_create_as_completed.add(name)

    actions = []
    for (name, _, eventstr, ids) in game_data:
        if eventstr == "+" and name in names_to_create:
            actions.append(CREATE_TASK_CURL % (secrets[PAT], name, linked_name(name, ids), secrets[PROJECT_ID]))
        elif eventstr == "+" and name in names_to_create_as_completed:
            actions.append(CREATE_COMPLETED_TASK_CURL % (secrets[PAT], name, linked_name(name, ids), secrets[PROJECT_ID]))
        if eventstr == "-" and name in names_to_complete:
            actions.append(COMPLETE_TASK_CURL % (tasks_by_name[name]["gid"], secrets[PAT]))

    for action in actions:
        print(action)
        subprocess.run(action, shell=True)
        time.sleep(1)


def get_args():
    parser = argparse.ArgumentParser()

    mutex = parser.add_mutually_exclusive_group()
    
    # utility to list workspaces and projects to initialize the secrets file
    mutex.add_argument(
        "--list-workspaces",
        action="store_true",
        help="list workspaces visible given PAT secret",
    )
    
    mutex.add_argument(
        "--list-projects",
        action="store_true",
        help="list projects visible given PAT and workspace secrets",
    )

    mutex.add_argument(
        "--list-tasks",
        action="store_true",
        help="list tasks visible given PAT and project secrets",
    )

    mutex.add_argument(
        "--update-tasks",
        action="store_true",
        help="update tasks based on data.txt changes",
    )

    args = parser.parse_args()

    return args


def main():
    args = get_args()
    
    secrets = load_secrets()
    
    if not secrets[PAT]:
        print("cannot use Asana API without a PAT")
        quit()
    
    #configuration = asana.Configuration()
    #configuration.access_token = secrets[PAT]
    #api_client = asana.ApiClient(configuration)
    
    if args.list_workspaces:
        workspaces = get_workspaces(secrets)
        print("Workspaces:")
        for workspace in workspaces:
            print("{}\t{}".format(workspace["gid"], workspace["name"]))
        quit()

    if not secrets[WORKSPACE_ID]:
        print("cannot make workspace-specific API calls without a workspace ID")
        quit()

    if args.list_projects:
        projects = get_projects(secrets)
        print("Projects:")
        for project in projects:
            print("{}\t{}".format(project["gid"], project["name"]))
        quit()

    if not secrets[PROJECT_ID]:
        print("cannot make project-specific API calls without a project ID")
        quit()

    if args.list_tasks:
        tasks = get_tasks(secrets)
        print(tasks)
        print("Tasks:")
        for task in tasks:
            print("{}\t{}".format(task["name"], task["completed"]))
        quit()

    if args.update_tasks:
        update_tasks(secrets)


if __name__ == '__main__':
    main()
