#!/usr/bin/python3

import argparse
from collections import defaultdict
import sys

import asana
from asana.rest import ApiException


ASANA_SECRETS_FILE = "secrets/asana-secrets.json"

PAT = "pat"
WORKSPACE_ID = "workspace_id"
PROJECT_ID = "project_id"


def quit():
    sys.exit(0)

def load_secrets():
    if not os.exists(ASANA_SECRETS_FILE):
        print("secrets file {} does not exist".format(ASANA_SECRETS_FILE))
        quit()

    with open(ASANA_SECRETS_FILE) as f:
        blob = f.read()
    try:
        data = json.loads(blob)
    except Exception as e:
        print("malformed secrets file {}".format(ASANA_SECRETS_FILE))
        quit()

    secrets = defaultdict(lambda: None)
    for key in data:
        if data[key]:
            secrets[key] = data[key]

    return secrets


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

    args = parser.parse_args()

    return args


def main():
    args = parser.parse_args()
    
    secrets = load_secrets()
    
    if not secrets[PAT]:
        print("cannot use Asana API without a PAT")
        quit()
    
    configuration = asana.Configuration()
    configuration.access_token = secrets[PAT]
    api_client = asana.ApiClient(configuration)
    
    if args.list_workspaces:
        workspaces = get_workspaces(api_client)
        print("Workspaces:")
        for workspace in workspaces:
            print("{}\t{}".format(workspace["gid"], workspace["name"]))
        quit()

    if not secrets[WORKSPACE_ID]:
        print("cannot make workspace-specific API calls without a workspace ID")
        quit()

    if args.list_projects:
        projects = get_projects(api_client, {"workspace": secrets[WORKSPACE_ID]})
        print("Projects:")
        for project in projects:
            print("{}\t{}".format(project["gid"], project["name"]))
        quit()

    if not secrets[PROJECT_ID]:
        print("cannot make project-specific API calls without a project ID")
        quit()



if __name__ == '__main__':
    main()
