import csv
import os
import subprocess
import shutil
import ast
import sys
import time
from pathlib import Path

import requests
from git import Repo, exc, Git

import logging
logger = logging.getLogger(__name__)
import settings
config = settings.get_config()
token = config['github_token']

# 1. Read CSV that has 2 columns: repo_patch_url, repo_base_url (done)
# 2. Using the github_repo_url to clone the repo to local (done)
# 3. download the patches to memory using github_patch_url (done)
# 4. Iteratively checkout to all the tags and apply the patch to each checkout (done)
# 5. If successful, create a new tag "***-secure". If not, ignore (done)
# 5a. count the number of successful tag (done)
# 6. Push the repo to remote. Go back to step 2 and repeat the process

patched_counter = 0

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
        data = [row for i, row in enumerate(csv_reader) if start_row <= i < end_row]
    return data

def get_org_library_name(url: str) -> tuple[str, str]:
    # sample: http://github.com/Illydth/wowraidmanager
    split_path = url.split('/')
    org_name = split_path[-2]
    library_name = split_path[-1].replace('.git','')
    return (org_name, library_name)

def clone_to_local_repo(repo_base_url: str) -> Repo:
    org_name, library_name = get_org_library_name(repo_base_url)
    
    if not os.path.exists('./repo'):
        os.makedirs('./repo')

    repo_path: str = os.path.join(os.getcwd(), 'repo', f'{org_name}_{library_name}')
    git_ssh_cmd = get_git_ssh_cmd()
    
    if not os.path.exists(repo_path) or not os.listdir(repo_path):
        try:
            git_ssh_clone_url = f'git@github.com:scantist-ossops/{library_name}.git'
            print(f"Cloning {git_ssh_clone_url} to local. This process will take a while.")
            repo = Repo.clone_from(git_ssh_clone_url, repo_path, env=dict(GIT_SSH_COMMAND=git_ssh_cmd))
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
    commit_tags = {}
    for tag in tags:
        try:
            new_branch_name = f'{tag}-branch-secure'
            # Stash any uncommitted changes
            # stash_changes(repo)
            
            # Checkout the tag
            repo.git.checkout(tag, b=new_branch_name)

            # As long as there is a patch, it is considered a success
            is_patched = any(apply_one_patch(repo, patch) for patch in patches)
            # is_patched = False
            # for patch in patches:
            #     if apply_one_patch(repo, patch):
            #         is_patched = True

            # Once the tag is patched, there will be a new commit and a new tag named "<original tag>-secure"
            if not is_patched:
                continue

            # add all file changes
            repo.git.add('--all')

            commit_message = f"Applied patches to tag {tag}"
            new_commit = repo.index.commit(commit_message)

            new_tag_name = f"{tag}-secure"
            repo.create_tag(new_tag_name, ref=new_commit)
            patched_counter += 1
            commit_tags[new_commit] = new_tag_name
            print(f"Patch applied and committed successfully to tag {tag}. Tagged the commit as {new_tag_name}.")

            repo.remotes.origin.push(new_branch_name, tags=True)
            print(f"Pushed to remote repo successfully.")

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
    
def fork_repo_remote(repo_base_url: str) -> str:
    # fork from given url to scantist-ossops
    # return a url pointing to scantist-ossops
    org_name, library_name = get_org_library_name(repo_base_url)
    api_url = f"https://api.github.com/repos/{org_name}/{library_name}/forks"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"organization": "scantist-ossops"}

    if check_repo_exists(library_name):
        print(f"Repository: {api_url} already exists, skip fork")
        return f"http://github.com/scantist-ossops/{library_name}"

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Forked: {org_name}/{library_name} to scantist-ossops/{library_name}")
        time.sleep(1)
        return f"http://github.com/scantist-ossops/{library_name}"
    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred while forking repository: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    sys.exit(1)
    # command = [
    #     "curl", "-L",
    #     "-X", "POST",
    #     "-H", "Accept: application/vnd.github+json",
    #     "-H", f"Authorization: Bearer {token}",
    #     "-H", "X-GitHub-Api-Version: 2022-11-28",
    #     f"https://api.github.com/repos/{org_name}/{library_name}/forks",
    #     "-d", '{"organization":"scantist-ossops"}'
    # ]
    # if check_repo_exists(library_name):
    #     print(f"Repository: https://api.github.com/repos/{org_name}/{library_name}/forks already exists, skip fork")
    #     return f"http://github.com/scantist-ossops/{library_name}"
    # try:
    #     subprocess.run(command, stdout=subprocess.PIPE, check=True)
    #     print(f"Forked: {org_name}/{library_name} to scantist-ossops/{library_name}")
    #     time.sleep(1)
    #     return f"http://github.com/scantist-ossops/{library_name}"
    # except subprocess.CalledProcessError as e:
    #     print(f"Error forking repository: {e}")
    # except Exception as e:
    #     print(f"An unexpected error occured: {e}")
    # sys.exit(1)

def get_git_ssh_cmd():
    # the file id_ed25519 is the ssh file that your command line environment
    # uses to authenticate ssh git clone
    private_key_path = config['private_key_path']
    file_path = Path(private_key_path)
    git_ssh_identity_file = file_path.resolve()
    return f'ssh -i {git_ssh_identity_file}'


def main():
    global patched_counter
    csv_file_path = 'final_data_v3.csv'
    csv_data: list = read_csv_to_variable(csv_file_path, start_row=0, end_row=2)
    
    for repo_patch_dict in csv_data:
        scantist_ossops_base_url = fork_repo_remote(repo_patch_dict['repo_base_url'])
        repo = clone_to_local_repo(scantist_ossops_base_url)
        if not repo:
            continue
        repo_patch_urls = parse_literal_to_list(repo_patch_dict['repo_patch_urls'])
        patches = [download_patch(url) for url in repo_patch_urls]
        apply_patches_to_repo(repo, patches)
        # Once the patches are done, delete the local repo
        delete_local_repo(repo)

    print(f'Total versions patched: {patched_counter}')

if __name__ == '__main__':
    main()