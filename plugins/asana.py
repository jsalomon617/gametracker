#!/usr/bin/python3

import argparse
from collections import defaultdict
import datetime
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen

#import asana
#from asana.rest import ApiException


ASANA_SECRETS_FILE = "plugins/secrets/asana-secrets.json"
DATA_FILE = "data.txt"

PAT = "pat"
WORKSPACE_ID = "workspace_id"
PROJECT_ID = "project_id"
CUSTOM_FIELDS = "custom_fields"

CF_TIME_LOWER = "time_lower"
CF_TIME_UPPER = "time_upper"
CF_WEIGHT = "weight"
CF_BGG_ID = "bgg_id"
CF_PLAYERS_LOWER = "players_lower"
CF_PLAYERS_UPPER = "players_upper"
CF_RATING = "rating"
CF_KEYS = [
    CF_TIME_LOWER,
    CF_TIME_UPPER,
    CF_WEIGHT,
    CF_BGG_ID,
    CF_PLAYERS_LOWER,
    CF_PLAYERS_UPPER,
    CF_RATING,
]


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

def save_secrets():
    if not os.path.exists(ASANA_SECRETS_FILE):
        with open(ASANA_SECRETS_FILE, 'w'):
            pass
    
    secrets = load_secrets()
    
    if PAT not in secrets:
        secrets[PAT] = input("Provide Asana PAT: ")
    
    if WORKSPACE_ID not in secrets:
        list_workspaces(secrets)
        secrets[WORKSPACE_ID] = input("Provide Workspace ID: ")

    if PROJECT_ID not in secrets:
        list_projects(secrets)
        secrets[PROJECT_ID] = input("Provide Project ID: ")

    if CUSTOM_FIELDS not in secrets:
        secrets[CUSTOM_FIELDS] = dict()

    missing_cfs = [
        key
        for key in CF_KEYS
        if key not in secrets[CUSTOM_FIELDS]
    ]
    if len(missing_cfs) > 0:
        list_custom_fields(secrets)
        for key in missing_cfs:
            secrets[CUSTOM_FIELDS][key] = input("Provide CF '{}' ID: ".format(key))

    # save the secrets
    with open(ASANA_SECRETS_FILE, 'w') as f:
        f.write(json.dumps(secrets, indent=4) + "\n")

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
     --url 'https://app.asana.com/api/1.0/tasks?project={project_id}&opt_fields=name,completed,custom_fields' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer {pat}'
"""

CUSTOM_FIELDS_CURL = """
curl --request GET \
     --url https://app.asana.com/api/1.0/projects/{project_id}/custom_field_settings?opt_fields=custom_field.name,custom_field.gid \
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

def get_custom_fields(secrets):
    return run_and_parse_curl(CUSTOM_FIELDS_CURL.format(pat=secrets[PAT], project_id=secrets[PROJECT_ID]))


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
     --data @- <<EOF
{
  "data": {
    %s
    "name": "%s",
    "html_notes": "<body>%s</body>",
    "projects": [
      "%s"
    ]
  }
}
EOF
"""

CREATE_COMPLETED_TASK_CURL = """
curl --request POST \
     --url 'https://app.asana.com/api/1.0/tasks' \
     --header 'accept: application/json' \
     --header 'authorization: Bearer %s' \
     --header 'content-type: application/json' \
     --data @- <<EOF
{
  "data": {
    %s
    "completed": true,
    "name": "%s",
    "html_notes": "<body>%s</body>",
    "projects": [
      "%s"
    ]
  }
}
EOF
"""

UPDATE_TASK_CURL = """
curl --request PUT \
     --url https://app.asana.com/api/1.0/tasks/%s \
     --header 'accept: application/json' \
     --header 'authorization: Bearer %s' \
     --header 'content-type: application/json' \
     --data '
{
  "data": %s
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

def task_updates_needed(secrets, task, ids):
    needed = set()
    if ids is None:
        # without a BGG id we can't do anything
        return needed

    for cf in task["custom_fields"]:
        for key in CF_KEYS:
            if cf["gid"] == secrets[CUSTOM_FIELDS][key] and cf["number_value"] is None:
                needed.add(key)
    return needed


def bgg_lookups(bgg_ids):
    #URL = "https://www.boardgamegeek.com/xmlapi/boardgame/" + ",".join(bgg_ids)
    URL = "https://www.boardgamegeek.com/xmlapi2/thing?id={}&stats=1".format(",".join(bgg_ids))
    cmd = 'wget -O - "%s"' % URL
    result = str(subprocess.run(cmd, shell=True, capture_output=True).stdout)

    ignored_keys = {
        "id-initial-ignore",
    }
    
    info = [
        ("id-initial-ignore", '<item type="', '"'),
        ("id", 'id="', '"'),
        (CF_PLAYERS_LOWER, '<minplayers value="', '"'),
        (CF_PLAYERS_UPPER, '<maxplayers value="', '"'),
        (CF_TIME_LOWER, '<minplaytime value="', '"'),
        (CF_TIME_UPPER, '<maxplaytime value="', '"'),
        (CF_RATING, '<average value="', '"'),
        (CF_WEIGHT, '<averageweight value="', '"'),
    ]
    
    data = {}
    for bgg_id in bgg_ids:
        blob = {}
        for (key, start, end) in info:
            if start not in result:
                print("Error: key '{}' start '{}' not in result for blob '{}'".format(key, start, blob))
                print(result)
                quit()
            if end not in result:
                print("Error: key '{}' end '{}' not in result for blob '{}'".format(key, end, blob))
                print(result)
                quit()
            item, result = result.split(start, 1)[1].split(end, 1)
            if key not in ignored_keys:
                blob[key] = item
        data[blob["id"]] = blob
    
    return data


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
    names_to_update = set()
    keys_to_update_per_name = defaultdict(set)
    gamedata_by_name = {}
    for (name, _, eventstr, ids) in game_data:
        if eventstr == "+":
            # first time we're seeing the game in the list
            gamedata_by_name[name] = [str(id) for id in ids] if ids else None
            if name not in tasks_by_name:
                # need to create a task
                names_to_create.add(name)
            else:
                # may need to update the task
                keys_to_update = task_updates_needed(secrets, tasks_by_name[name], ids)
                if len(keys_to_update) > 0:
                    names_to_update.add(name)
                    for key in keys_to_update:
                        keys_to_update_per_name[name].add(key)
        elif eventstr == "-":
            # second time we're seeing the game in the list
            if name in tasks_by_name:
                # already have a task, may need to complete it
                if not tasks_by_name[name]["completed"]:
                    names_to_complete.add(name)
            elif name in names_to_create:
                # no task yet, but since we're seeing it for the second time, let's move
                # the creation here
                names_to_create.remove(name)
                names_to_create_as_completed.add(name)

    task_puts = defaultdict(dict)
    for name in names_to_complete:
        task_puts[name]["completed"] = True
    
    bgg_ids = []
    for name in names_to_update.union(names_to_create).union(names_to_create_as_completed):
        if gamedata_by_name[name]:
            bgg_ids.extend(gamedata_by_name[name])
    bggdata = bgg_lookups(bgg_ids) if bgg_ids else {}

    for name in names_to_update.union(names_to_create).union(names_to_create_as_completed):
        cfs = {}
        task_puts[name]["custom_fields"] = cfs
        ids = gamedata_by_name[name]
        if ids:
            use_id = ids[0]
            if CF_BGG_ID in keys_to_update_per_name[name]:
                cfs[secrets[CUSTOM_FIELDS][CF_BGG_ID]] = use_id
            if use_id in bggdata:
                for key in keys_to_update_per_name[name]:
                    cfs[secrets[CUSTOM_FIELDS][key]] = bggdata[use_id][key]

    actions = []
    for name, ids in gamedata_by_name.items():
        task_puts_json = json.dumps(task_puts[name]) if name in task_puts else ""
        if name in names_to_create:
            actions.append(CREATE_TASK_CURL % (secrets[PAT], task_puts_json + ",", name, linked_name(name, ids), secrets[PROJECT_ID]))
        elif name in names_to_create_as_completed:
            actions.append(CREATE_COMPLETED_TASK_CURL % (secrets[PAT], task_puts_json + ",", name, linked_name(name, ids), secrets[PROJECT_ID]))
        #elif name in names_to_complete:
        #    actions.append(COMPLETE_TASK_CURL % (tasks_by_name[name]["gid"], secrets[PAT]))
        elif name in task_puts:
            actions.append(UPDATE_TASK_CURL % (tasks_by_name[name]["gid"], secrets[PAT], task_puts_json))

    for action in actions:
        print(action)
        subprocess.run(action, shell=True)
        time.sleep(1)

    print()


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--update-secrets",
        action="store_true",
        help="bring the secrets file up to date, possibly with prompts as necessary",
    )

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
        "--list-custom-fields",
        action="store_true",
        help="list custom fields visible on project given secrets",
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


def list_workspaces(secrets):
    workspaces = get_workspaces(secrets)
    print("Workspaces:")
    for workspace in workspaces:
        print("{}\t{}".format(workspace["gid"], workspace["name"]))


def list_projects(secrets):
    projects = get_projects(secrets)
    print("Projects:")
    for project in projects:
        print("{}\t{}".format(project["gid"], project["name"]))

def list_custom_fields(secrets):
    cfs = get_custom_fields(secrets)
    print("Custom Fields:")
    for cf in cfs:
        cf = cf["custom_field"]
        print("{}\t{}".format(cf["gid"], cf["name"]))
    

def main():
    args = get_args()

    if args.update_secrets:
        save_secrets()
        quit()

    secrets = load_secrets()
    
    if not secrets[PAT]:
        print("cannot use Asana API without a PAT")
        quit()
    
    #configuration = asana.Configuration()
    #configuration.access_token = secrets[PAT]
    #api_client = asana.ApiClient(configuration)
    
    if args.list_workspaces:
        list_workspaces(secrests)
        quit()

    if not secrets[WORKSPACE_ID]:
        print("cannot make workspace-specific API calls without a workspace ID")
        quit()

    if args.list_projects:
        list_projects(secrets)
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

    if args.list_custom_fields:
        list_custom_fields(secrets)
        quit()

    if args.update_tasks:
        update_tasks(secrets)


if __name__ == '__main__':
    main()
