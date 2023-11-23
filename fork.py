# First create a personal token in github settings/developer settings/personal
# access tokens/ Tokens(classic) and use that after Bearer.

import subprocess
import time
import json
import os
import logging

# Initialize the logger in fork.py
logger = logging.getLogger('main')  # Get the logger instance from main.py

def set_logger(main_logger):
    global logger
    logger = main_logger

# CHANGE TOKEN ACCORDING TO USER
TOKEN = ""

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
        logger.info(f"Repository: https://api.github.com/repos/{org_name}/{library_name}/forks already exists, skip fork")
        return True
    else:
        try:
            subprocess.run(command, shell=True, stdout=subprocess.PIPE)
            logger.info(f"Forked: {org_name}/{library_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.info(f"Error forking repository: {e}")
            return False
        except Exception as e:
            logger.info(f"An unexpected error occured: {e}")
            return False
    
def get_scantist_ossops_remote_path(repo_remote_path, username='', password=''):
    # given: https://github.com/Cacti/cacti.git
    # output: https://github.com/scantist-ossops/cacti.git
    split_path = repo_remote_path.split('/')
    split_path[-2] = "scantist-ossops"
    #split_path[2] = f"{username}:{password}@github.com"
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
        logger.info(f"Error: {result.stderr.strip()}")

    try:
        response_dict["message"] == "Not Found"
        return False
    except:
        return True
    
def get_all_tags(org_name, library_name):
    # all the tags should be gotten from scantist-ossops when the fork is fresh
    # in local
    tag_names = []
    command = f"""curl -I -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer {TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        https://api.github.com/repos/scantist-ossops/{library_name}/tags \
        | grep '^link:' \
        | sed -e 's/^link:.*page=//g' -e 's/>.*$//g'
        """
    last_page = subprocess.run(command, shell=True, capture_output=True, text=True)
    if last_page.stdout:
        # need to take into account pagination
        for p in range(1, int(last_page.stdout)+1):
            command = f"""curl -v \
                -H "Accept: application/vnd.github+json" \
                -H "Authorization: Bearer {TOKEN}" \
                -H "X-GitHub-Api-Version: 2022-11-28" \
                https://api.github.com/repos/scantist-ossops/{library_name}/tags?page={p} \
                """
            process_result = subprocess.run(command, shell=True, capture_output=True, text=True)
            tag_data = json.loads(process_result.stdout)
            tag_names.extend(tag['name'] for tag in tag_data)
    else:
        command = f"""curl -v \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer {TOKEN}" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            https://api.github.com/repos/scantist-ossops/{library_name}/tags \
            """ 
        process_result = subprocess.run(command, shell=True, capture_output=True, text=True)
        tag_data = json.loads(process_result.stdout)
        tag_names.extend(tag['name'] for tag in tag_data)      
    return tag_names

def clone_scantist_repo(library_name):
    # add the --config if need to include private key file
    # git clone git@provider.com:userName/projectName.git --config core.sshCommand="ssh -i ~/location/to/private_ssh_key"
    command = f"""git -C ./scantist-ossops/ clone git@github.com:scantist-ossops/{library_name}.git
        """
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)

def git_fetch():
    command = f""" git fetch --all --tags --prune
        """
    git_fetch = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_fetch

def check_out_tag(repo_path, tag_ref):
    temp_branch_name = f'{tag_ref}-branch-secure'
    # move directory to git repo directory
    os.chdir(repo_path)
    # make sure all tag exists, fetch first
    git_fetch1 = git_fetch()
    command = f""" git checkout tags/{tag_ref} -b {temp_branch_name}
        """
    try:
        git_checkout = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    except:
        # branch might be created already, check it out instead
        command = f""" git checkout {temp_branch_name}
        """
        git_checkout = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)

def checkout_branch(repo_path, tag_ref):
    branch_name = f'{tag_ref}-branch-secure'
    os.chdir(repo_path)
    command = f""" git checkout {branch_name}
        """
    git_checkout = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    if git_checkout.stdout:
        logger.info(f"Command: {command} output: {git_checkout.stdout}")
    return
    
def git_push(tag_ref):
    temp_branch_name = f'{tag_ref}-branch-secure'
    command = f""" git push --set-upstream origin {temp_branch_name}
        """
    git_push1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_push1.stdout

def git_add(target_file):
    command = f""" git add {target_file}
        """
    git_add1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_add1.stdout

def git_commit():
    command = f""" git commit -m "Patch vulnerability in older version"
        """
    git_commit1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_commit1.stdout

def git_create_tag(tag_ref):
    tag_name = tag_ref + '-secure'
    command = f""" git tag {tag_name}
        """
    git_tag1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_tag1.stdout

def git_rebase(tag_ref):
    branch_name = tag_ref + '-branch-secure'
    command = f"""git rebase origin/{branch_name}
        """
    git_rebase1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_rebase1.stdout

def git_push_tags():
    command = f""" git push --tags
        """
    git_push_tags1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return git_push_tags1.stdout   

def git_add_commit_push_create_tag(repo_path, target_file, tag_ref):
    print(os.getcwd())
    if os.getcwd() == repo_path:
        git_add1 = git_add(target_file)
        git_commit1 = git_commit()
        try:
            git_push1 = git_push(tag_ref)
        except:
            git_rebase1 = git_rebase(tag_ref)
            git_push1 = git_push(tag_ref)
        git_create_tag1 = git_create_tag(tag_ref)
        git_push_tags1 = git_push_tags()
    else:
        os.chdir(repo_path)
        git_add1 = git_add(target_file)
        git_commit1 = git_commit()
        try:
            git_push1 = git_push(tag_ref)
        except:
            git_rebase1 = git_rebase(tag_ref)
            git_push1 = git_push(tag_ref)
        git_create_tag1 = git_create_tag(tag_ref)
        git_push_tags1 = git_push_tags()
    return

def get_secured_tag_counts():
    # only run after all patching is done to get a total count of tags with 
    # -secure
    secure_tag_count = 0
    repo_names = get_org_repo()
    for repo_name in repo_names:
        tags_list = get_all_tags('scantist-ossops', repo_name)
        for tag_name in tags_list:
            if "-secure" in tag_name:
                secure_tag_count += 1
    return secure_tag_count

def get_org_repo():
    repo_names=[]
    command = f"""curl -L \
        -X GET \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer {TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        https://api.github.com/orgs/scantist-ossops/repos
        """ 
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    repo_data = json.loads(result.stdout)
    repo_names.extend(repo['name'] for repo in repo_data)
    return repo_names

def parse_patchhunk_json(json_filename):
    with open(json_filename, 'r') as json_file:
        data = json.load(json_file)
        for cve_id, value in data.items():
            for dict1 in value:
                git_url_list = dict1['git_url']
                relative_filepath = dict1['affected_file']
                vuln_unicode = dict1['vuln_unicode']
                patched_unicode = dict1['patched_unicode']
                yield (git_url_list, relative_filepath, vuln_unicode, patched_unicode)

def get_org_library_name(git_url: str) -> tuple:
    """
    Extract and return the organization's and library's name from a Git remote URL.

    The function splits the URL by '/' and extracts the last two segments as the organization and library names. 
    It assumes the URL is in the standard format: 'https://github.com/<organization>/<library>.git' or a similar format.

    Parameters:
    git_url (str): A string representing the Git remote URL. Expected to be a valid URL in the standard Git format.

    Returns:
    tuple: A tuple where the first element is the organization's name (str) and the second element is the library's name (str).
    
    Example:
    >>> get_org_library_name('https://github.com/exampleOrg/exampleRepo.git')
    ('exampleOrg', 'exampleRepo')

    Note:
    The function does not validate the URL format and may produce incorrect results or errors if the URL is non-standard.
    """
    split_path = git_url.split('/')
    org_name = split_path[-2]
    library_name = split_path[-1].replace('.git','')
    return (org_name, library_name)

def update_forked_repo(repo_path, git_url):
    # In your local clone of your forked repository, you can add the original 
    # GitHub repository as a "remote". ("Remotes" are like nicknames for the 
    # URLs of repositories - origin is one, for example.) Then you can fetch 
    # all the branches from that upstream repository, and rebase your work to 
    # continue working on the upstream version.

    # move to correct directory for the git command to work
    os.chdir(repo_path)
    try:
        command = f""" git remote add upstream {git_url}
            """
        git_cmd1 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        if git_cmd1.stdout:
            logger.info(f"Command: {command} output: {git_cmd1.stdout}")
    except:
        logger.info("upstream already exists")

    command = f""" git fetch upstream
        """
    git_cmd2 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    if git_cmd2.stdout:
        logger.info(f"Command: {command} output: {git_cmd2.stdout}")
    try:
        command = f""" git checkout master
            """
        git_cmd3 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    except:
        command = f""" git checkout main
            """
        git_cmd3 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    if git_cmd3.stdout:
        logger.info(f"Command: {command} output: {git_cmd3.stdout}")

    try:
        command = f""" git rebase upstream/master
            """
        git_cmd4 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        if git_cmd4.stdout:
            logger.info(f"Command: {command} output: {git_cmd4.stdout}")
    except:
        command = f""" git rebase upstream/main
            """
        git_cmd4 = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        if git_cmd4.stdout:
            logger.info(f"Command: {command} output: {git_cmd4.stdout}")
    return
