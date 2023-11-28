import csv
import os
import subprocess
import shutil
import ast
import sys

import requests
from git import Repo, exc

import config_loader

# 1. Read CSV that has 2 columns: repo_patch_url, repo_base_url (done)
# 2. Using the github_repo_url to clone the repo to local (done)
# 3. download the patches to memory using github_patch_url (done)
# 4. Iteratively checkout to all the tags and apply the patch to each checkout (done)
# 5. If successful, create a new tag "***-secure". If not, ignore (done)
# 5a. count the number of successful tag
# 6. Push the repo to remote. Go back to step 2 and repeat the process

patched_counter = 0

config = config_loader.get_config()
token = config['github_token']

def check_repo_exists(library_name: str) -> bool:
    url = f"https://api.github.com/repos/scantist-ossops/{library_name}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Will raise an error for 4XX/5XX responses
        return True if response.status_code == 200 else False
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            return False
        print(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    sys.exit(1)

def read_csv_to_variable(file_path: str, start_row: int = 0, end_row: int = 100):
    data = []
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for i, row in enumerate(csv_reader):
            if start_row <= i < end_row:
                data.append(row)
            elif i >= end_row:
                break
    return data

def get_org_library_name(url: str) -> tuple[str, str]:
    split_path = url.split('/')
    org_name = split_path[-2]
    library_name = split_path[-1].replace('.git','')
    return (org_name, library_name)

def clone_to_local_repo(repo_base_url: str) -> Repo:
    org_name, library_name = get_org_library_name(repo_base_url)

    if not os.path.exists('./repo'):
        os.makedirs('./repo')

    repo_path: str = os.path.join(os.getcwd(), 'repo', f'{org_name}_{library_name}')
    
    if not os.path.exists(repo_path) or not os.listdir(repo_path):
        try:
            print(f"Cloning {repo_base_url} to local. This process will take a while.")
            repo = Repo.clone_from(repo_base_url, repo_path)
        except exc.GitCommandError as e:
            print(f"Git command error occurs at clone process: {e}")
            return None

    repo = Repo(repo_path)
    print(f"Successfully cloned {repo_base_url} to local")
    return repo

def delete_local_repo(repo: Repo):
    shutil.rmtree(repo.working_dir)

def download_patch(url: str) -> str:
    try:
        with requests.get(url) as r:
            r.raise_for_status()
            print(f"Successfully downloaded patch {url}")
            return r.text
    except Exception as e:
        print(f'Error downloading the patch: {e}')

def get_git_tags(repo: Repo) -> list:
    tags = [tag.name for tag in repo.tags]
    return tags

def stash_changes(repo: Repo):
    if repo.is_dirty():
        repo.git.stash('save', 'Automated stash by GitPython')

def apply_patches_to_repo(repo: Repo, patches: list):
    global patched_counter
    tags = get_git_tags(repo)
    for tag in tags:
        try:
            # Stash any uncommitted changes
            stash_changes(repo)
            
            # Checkout the tag
            repo.git.checkout(tag)

            # As long as there is a patch, it is considered a success
            is_patched = False
            for patch in patches:
                if apply_one_patch(repo, patch):
                    is_patched = True

            # Once the tag is patched, there will be a new commit and a new tag named "<original tag>-secure"
            if not is_patched:
                continue

            commit_message = f"Applied patches to tag {tag}"
            new_commit = repo.index.commit(commit_message)

            new_tag_name = f"{tag}-secure"
            repo.create_tag(new_tag_name, ref=new_commit)
            patched_counter += 1
            print(f"Patch applied and committed successfully to tag {tag}. Tagged the commit as {new_tag_name}.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

def apply_one_patch(repo: Repo, patch_content):
    try:
        # Start a subprocess running 'git apply'
        proc = subprocess.Popen(['git', 'apply', '-'], cwd=repo.working_dir, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=patch_content.encode())
        if proc.returncode == 0:
            return True
    except Exception as e:
        print(f"Error applying a patch: {e}")
        
    return False

def parse_literal_to_list(string):
    try:
        return ast.literal_eval(string)
    except ValueError:
        return []
    
def main():
    print(check_repo_exists('abc'))
    return
    global patched_counter
    # Path to your CSV file
    csv_file_path = 'final_data_v3.csv'

    # Read the CSV data into a Python variable
    csv_data: list = read_csv_to_variable(csv_file_path, start_row=0, end_row=10)
    
    for repo_patch_dict in csv_data:
        # TODO: fork_repo_remote(): fork in remote, change repo_base_url to scantist_ossops_base_url, change clone_to_local_repo argument to scantist_ossops_base_url
        repo = clone_to_local_repo(repo_patch_dict['repo_base_url'])
        if not repo:
            continue
        repo_patch_urls = parse_literal_to_list(repo_patch_dict['repo_patch_urls'])
        patches = []
        for url in repo_patch_urls:
            patches.append(download_patch(url))
        apply_patches_to_repo(repo, patches)
        # TODO: push_local_to_remote(repo): push local repo to remote repo
        # Once the patches are done, delete the local repo
        delete_local_repo(repo)

    print(f'Total versions patched: {patched_counter}')

if __name__ == '__main__':
    main()