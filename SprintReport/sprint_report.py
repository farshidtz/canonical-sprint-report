import argparse
import re
import json

from jira import JIRA, JIRAError
from SprintReport.jira_api import jira_api

from pprint import pprint

jira_server = ""


def get_bug_id(summary):
    "Extract the bug id from a jira title which would include LP#"
    id = ""

    if "LP#" in summary:
        for char in summary[summary.find("LP#")+3:]:
            if char.isdigit():
                id = id + char
            else:
                break

    return id


def find_issue_in_jira_sprint(jira_api, project, sprint):
    if not jira_api or not project:
        return {}

    # Get JIRA issues in batch of 50
    issue_index = 0
    issue_batch = 50

    found_issues = {}

    while True:
        start_index = issue_index * issue_batch
        request = "project = {} " \
            "AND sprint = \"{}\" " \
            "ORDER BY parent ASC".format(project, sprint)
        issues = jira_api.search_issues(request, startAt=start_index)

        if not issues:
            break

        issue_index += 1

        # For each issue in JIRA with LP# in the title
        for issue in issues:
            # pprint(vars(issue))
            # break
            summary = issue.fields.summary
            issue_type = issue.fields.issuetype.name
            found_issues[issue.key] = {
                "key": issue.key,
                "status": issue.fields.status,
                "type": issue_type,
                "summary": summary,
                "labels": issue.fields.labels}

            if hasattr(issue.fields, 'parent'):
                # print(vars(issue.fields.parent))
                found_issues[issue.key]["parent-key"] = issue.fields.parent.key
                found_issues[issue.key]["parent-summary"] = issue.fields.parent.fields.summary

    return found_issues


def key_to_md(key):
    global jira_server
    markdown_link = "[{}]({})"

    return markdown_link.format(key, jira_server + "/browse/" + key)


def summary_to_md(key, summary):
    global jira_server
    markdown_link = "[{}]({})"

    return markdown_link.format(summary, jira_server + "/browse/" + key)

def insert_bug_link(text):
    markdown_link = "[{}]({})"
    bugid = get_bug_id(text)
    bug = "LP#" + bugid
    link = "https://pad.lv/" + bugid

    return re.sub(bug, markdown_link.format(bug, link), text)


def print_jira_issue(issue):
    status = issue["status"]
    issue_md = summary_to_md(issue["key"], issue["summary"])
    
    icon = None
    reason = None
    match str(status):
        case "Done":
            icon = ":white_check_mark:"
        case "Rejected":
            icon = ":negative_squared_cross_mark:"
        case _: # "In Progress", "In Review", "Untriaged", "Triaged"
            icon = ":warning:"
            reason = status

    if issue["type"] == "Bug":
        icon += ' :beetle:'

    if 'Carry-over' in issue["labels"]:
        icon += ' :arrow_right_hook:'

    print(" - {} {}".format(icon, issue_md))
    if reason:
        print("   - {}".format(reason))


def print_jira_report(issues):
    if not issues:
        return

    global sprint
    print("# {} report".format(sprint))

    parent = ""
    for issue in issues:
        if issues[issue]["parent-key"] != parent:
            parent = issues[issue]["parent-key"]

            # Print parent details
            print("\n### {}".format(summary_to_md(
                parent, issues[issue]["parent-summary"])))

        print_jira_issue(issues[issue])


def main(args=None):
    global jira_server
    global sprint
    parser = argparse.ArgumentParser(
        description="A script to return a a Markdown report of a Jira Sprint"
    )

    parser.add_argument("project", type=str, help="key of the Jira project")
    parser.add_argument("sprint", type=str, help="name os the Jira sprint")

    opts = parser.parse_args(args)

    try:
        api = jira_api()
    except ValueError:
        return "ERROR: Cannot initialize Jira API"

    jira_server = api.server

    jira = JIRA(api.server, basic_auth=(api.login, api.token))

    sprint = opts.sprint
    # Create a set of all Jira issues completed in a given sprint
    issues = find_issue_in_jira_sprint(jira, opts.project, sprint)
    print("Found {} issue{} in JIRA".format(
        len(issues), "s" if len(issues) > 1 else "")
    )

    print_jira_report(issues)

# =============================================================================
