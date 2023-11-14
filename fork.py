# First create a personal token in github settings/developer settings/personal
# access tokens/ Tokens(classic) and use that after Bearer.

import subprocess
import time
import json

# CHANGE TOKEN ACCORDING TO USER
TOKEN = "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"

def fork_repo_to_org(org_name, library_name):
    command = f"""curl -L \
        -X POST \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer {TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        https://api.github.com/repos/{org_name}/{library_name}/forks \
        -d '{{"organization":"scantist-ossops"}}'
        """
    if check_repo_exists(library_name):
        print("Repository already exists, skip fork")
        return
    else:
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        print(f"Forked: {org_name}/{library_name}")
    time.sleep(3)
    return

def get_scantist_ossops_remote_path(repo_remote_path):
    # given: https://github.com/Cacti/cacti.git
    # output: https://github.com/scantist-ossops/cacti.git
    split_path = repo_remote_path.split('/')
    split_path[-2] = "scantist-ossops"
    scantist_ossops_remote_path = '/'.join(split_path)
    return scantist_ossops_remote_path

def check_repo_exists(library_name):
    command = f"""curl -L \
        -X GET \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer {TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        https://api.github.com/repos/scantist-ossops/{library_name}
        """ 
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        response = result.stdout.strip()
        response_dict = json.loads(response)
    else:
        print(f"Error: {result.stderr.strip()}")

    try:
        response_dict["message"] == "Not Found"
        return False
    except:
        return True 
    