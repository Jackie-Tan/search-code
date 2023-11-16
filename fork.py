# First create a personal token in github settings/developer settings/personal
# access tokens/ Tokens(classic) and use that after Bearer.

import subprocess
import time
import json
import os

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
        print(f"Error: {result.stderr.strip()}")

    try:
        response_dict["message"] == "Not Found"
        return False
    except:
        return True
    
def get_all_tags(org_name, library_name):
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