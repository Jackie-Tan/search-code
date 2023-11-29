import csv
import os
import subprocess
import shutil
import ast
import sys
import time
from pathlib import Path
import argparse

import requests
from git import Repo, exc, Git

import logging
logger = logging.getLogger(__name__)
import settings
config = settings.get_config()
token = config['github_token']
private_key_path = config['private_key_path']

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
        logger.error(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request: {e}")

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
            logger.error(f"Git command error occurs at clone process: {e}")
            return None

    repo = Repo(repo_path)
    success_clone_statement: str = f'Successfully cloned {repo_base_url} to local'
    logger.info(success_clone_statement)
    print(success_clone_statement)
    return repo

def delete_local_repo(repo: Repo):
    shutil.rmtree(repo.working_dir)

def download_patch(url: str) -> str:
    try:
        with requests.get(url) as r:
            r.raise_for_status()
            success_download_statement: str = f'Successfully downloaded patch {url}'
            logger.info(success_download_statement)
            print(success_download_statement)
            return r.text
    except Exception as e:
        logger.error(f'Error downloading the patch: {e}')

def get_git_tags(repo: Repo) -> list:
    tags = [tag.name for tag in repo.tags]
    return tags

def stash_changes(repo: Repo):
    if repo.is_dirty():
        repo.git.stash('save', 'Automated stash by GitPython')

def apply_patches_to_repo(repo: Repo, patches: list) -> bool:
    global patched_counter
    tags = get_git_tags(repo)
    git_obj = Git(repo.working_dir)
    is_repo_patched = False
    for tag in tags:
        try:      
            # Checkout the tag
            git_obj.checkout(tag)

            # As long as there is a patch applied to the tag, it is a success
            is_patched = any(apply_one_patch(repo, patch) for patch in patches)            
            if not is_patched:
                continue

            # Once the tag is patched,a new branch, a new commit and a new tag named "<original tag>-secure" will be created
            new_branch_name = f'{tag}-branch-secure'
            new_branch_ref = repo.create_head(new_branch_name)
            new_branch_ref.checkout()
            logger.info(f"Successfully created new branch {new_branch_name}")

            repo.git.add('--all')

            new_commit = repo.index.commit(f"Applied patches to tag {tag}")

            repo.create_tag(new_tag_name := f"{tag}-secure", ref=new_commit)
            logger.info(f"Successfully applied patches to tag {tag}, committed and tagged as {new_tag_name}")

            repo.remotes.origin.push(new_branch_name, tags=True)
            logger.info(f"Successfully pushed to remote repo")
            patched_counter += 1
            is_repo_patched = True

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

    return is_repo_patched

def apply_one_patch(repo: Repo, patch_content):
    try:
        # Start a subprocess running 'git apply'
        proc = subprocess.Popen(['git', 'apply', '-'], cwd=repo.working_dir, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=patch_content.encode())
        if proc.returncode == 0:
            return True
    except Exception as e:
        logger.error(f"Error applying a patch: {e}")
        
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
        logger.warning(f"Repository: {api_url} already exists, skip fork")
        return None
        # return f"http://github.com/scantist-ossops/{library_name}"

    try:
        print(f'Forking {org_name}/{library_name} to scantist-ossops/{library_name}...')
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully forked {org_name}/{library_name} to scantist-ossops/{library_name}")
        time.sleep(1) # is it necessary to sleep for 1s here?
        return f"http://github.com/scantist-ossops/{library_name}"
    
    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred while forking repository: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

def get_git_ssh_cmd():
    global private_key_path
    file_path = Path(private_key_path)
    git_ssh_identity_file = file_path.resolve()
    return f'ssh -i {git_ssh_identity_file}'

def get_arguments():
    parser = argparse.ArgumentParser(description='Apply Patches')
    parser.add_argument('start_index', help='start index of the data')
    parser.add_argument('end_index', help='end index of the data (not inclusive)')
    return parser.parse_args()

def delete_github_repo(repo_base_url):
    """
    Delete a repository on GitHub.
    
    :param repo_base_url: Repository's remote base url (e.g. "https://github.com/<org_name>/<lib_name>")
    """
    org_name, library_name = get_org_library_name(repo_base_url)
    api_url = f'https://api.github.com/repos/{org_name}/{library_name}'
    headers = {"Authorization": f"token {token}"}

    response = requests.delete(api_url, headers=headers)

    if response.status_code == 204:
        logger.info(f'Successfully deleted repository {org_name}/{library_name}')
    else:
        logger.error(f"Failed to delete repository {org_name}/{library_name}. Status code: {response.status_code}")
        logger.error("Response:", response.json())

def main(args: argparse.Namespace):
    global patched_counter
    
    csv_file_path = 'final_data_v3.csv'
    csv_data: list = read_csv_to_variable(csv_file_path, start_row=int(args.start_index), end_row=int(args.end_index))
    
    for repo_patch_dict in csv_data:
        if (scantist_ossops_base_url := fork_repo_remote(repo_patch_dict['repo_base_url'])) is None:
            continue
        if (repo := clone_to_local_repo(scantist_ossops_base_url)) is None:
            continue
        repo_patch_urls = parse_literal_to_list(repo_patch_dict['repo_patch_urls'])
        patches = [download_patch(url) for url in repo_patch_urls]
        if not apply_patches_to_repo(repo, patches):
            print(f'No patches for repo {scantist_ossops_base_url}. Deleting the remote repo...')
            delete_github_repo(scantist_ossops_base_url)
        # Once the patches are done, delete the local repo
        delete_local_repo(repo)
    
    total_version_statement: str = f"Total versions patched: {patched_counter}"
    logger.info(total_version_statement)
    print(total_version_statement)

if __name__ == '__main__':
    args: argparse.Namespace = get_arguments()
    main(args)