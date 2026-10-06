#!/usr/bin/env python3
"""Read Pages configuration; keep the built artifact available if initial setup is still required."""

import json
import os
from pathlib import Path
import urllib.error
import urllib.request


def main():
    repository = os.environ.get("GITHUB_REPOSITORY", "Phattharaphum/nb-BioinformaticsProgramming")
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "nb-project-pages", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(f"https://api.github.com/repos/{repository}/pages", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            ready = json.load(response).get("build_type") == "workflow"
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        ready = False
    value = "true" if ready else "false"
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"ready={value}\n")
    message = ("GitHub Pages is configured for Actions; deployment will run." if ready else
               f"Website built successfully. One-time setup: open https://github.com/{repository}/settings/pages "
               "and choose Source: GitHub Actions. Then run this workflow again. "
               "The github-pages artifact contains the complete tested website.")
    print(message)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write("## Website deployment\n\n" + message + "\n")


if __name__ == "__main__":
    main()
