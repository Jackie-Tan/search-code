from git import Repo, exc
import logging
import os
import sys
import shutil
import json
import ast
import fork
import time
import glob
import warnings

def start_log():
    logger = logging.getLogger('main')

    # Configure root logger with basicConfig if no handlers are present
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(filename='git_org_repo.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    # Check if the 'main' logger already has handlers
    if not logger.hasHandlers():
        # Create and set up the file handler
        file_handler = logging.FileHandler('git_org_repo.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the handler to the 'main' logger
        logger.addHandler(file_handler)

    # Disable propagation to the root logger
    logger.propagate = False
    
    # Pass the logger to fork.py
    fork.set_logger(logger)

    logging.info('logger start')

def search_string(file, string_to_search):
    count = 0
    for line in file:
        if string_to_search in line:
            print("Exact match found.")
            count += 1
    return count

def search_and_patch(file, string_to_search, string_to_patch):
    patched = False
    patched_lines = []
    for line in file:
        if string_to_search in line:
            # print(f"FILE: {file}")
            # print(f"SEARCH STRING:{string_to_search}")
            # print(f"PATCH STRING: {string_to_patch}")
            # print(f"LINE FOUND: {line}")
            patched_lines.append(line.replace(string_to_search, string_to_patch))
            patched = True
        else:
            patched_lines.append(line)
    return (patched, patched_lines)

def get_org_library_names(repo_remote_path: str) -> tuple[str, str]:
    split_path = repo_remote_path.split('/')
    org_name = split_path[-2]
    library_name = split_path[-1].replace('.git','')
    return (org_name, library_name)

def get_library_name(repo_remote_path: str) -> str:
    return repo_remote_path.split('/')[-1].replace('.git','')

def parse_json(json_path: str) -> tuple[str, str, str]:
    with open(json_path, 'r') as json_file:
        data = json.load(json_file)
        for key, value in data.items():
            repo_remote_path = value['git_url']
            relative_filepath_str = value['patch_localized_filepath'][0]
            relative_filepath_list = ast.literal_eval(relative_filepath_str)
            relative_filepath = relative_filepath_list[0]
            string_to_search_str = value['line_changes'][0]
            string_to_search_dict = ast.literal_eval(string_to_search_str)
            try:
                string_to_search = string_to_search_dict[relative_filepath]['-'][0]
            except:
                string_to_search = '=============+++++++++++++++==============----------------'
            yield (repo_remote_path, relative_filepath, string_to_search)

def parse_json_with_patch(json_path: str) -> tuple[str, str, str]:
    with open(json_path, 'r') as json_file:
        data = json.load(json_file)
        for key, value in data.items():
            repo_remote_path = value['git_url']
            relative_filepath_str = value['patch_localized_filepath'][0]
            relative_filepath_list = ast.literal_eval(relative_filepath_str)
            relative_filepath = relative_filepath_list[0]
            string_to_search_str = value['line_changes'][0]
            string_to_search_dict = ast.literal_eval(string_to_search_str)
            try:
                string_to_search = string_to_search_dict[relative_filepath]['-'][0]
                string_to_patch = string_to_search_dict[relative_filepath]['+'][0]
            except:
                string_to_search = '=============+++++++++++++++==============----------------'
                string_to_patch = '=============+++++++++++++++==============----------------'

            yield (repo_remote_path, relative_filepath, string_to_search, string_to_patch)

def retry_operation(operation, max_retries=3, delay=3):
    retries=0
    while retries < max_retries:
        try:
            time.sleep(delay)
            operation()
            return
        except Exception as e:
            logging.error(f"Error: {e}")
            retries+=1
            logging.info(f"Retrying ({retries}/{max_retries}) after a short delay...")
            time.sleep(delay)
        except warnings.Warning as w:
            logging.warning(f"Warning: {w}")
            retries+=1
            logging.info(f"Retrying ({retries}/{max_retries}) after a short delay...")
            time.sleep(delay)

def push_rename_tag(repo, tag_ref, file_to_add, temp_branch_name):
    new_tag_name = tag_ref.name + '-secure'
    commit_message = "Patch vulnerability in older version"
    try:
        repo.create_head(temp_branch_name)
        repo.heads[temp_branch_name].checkout()
        print("TEMP BRANCH CREATED")
        # first push all file changes
        repo.index.add([file_to_add])
        repo.index.commit(commit_message)
        print(f"Commit created: {repo.head.commit}")
        retry_operation(lambda: repo.remotes.origin.push(temp_branch_name, kill_after_timeout=3.0))
        print(f"Pushed changes to {temp_branch_name}")
        temp_branch_commit = repo.commit(temp_branch_name)
        # create a new local tag from old tag, delete local tag and push new to
        # remote, delete old tag on origin
        repo.create_tag(new_tag_name, ref=temp_branch_commit)
        print(f"New tag created: {new_tag_name}")
        #print(f"delete {tag_ref.name}")
        #repo.delete_tag(tag_ref.name)
        #print(f"new tag {new_tag_name}")
        retry_operation(lambda: repo.remotes.origin.push(temp_branch_name, kill_after_timeout=3.0))
        print(f"Pushed new tag to {new_tag_name}")
    except Exception as e:
        print(f"Error: {e}")

def check_tag_exists(repo, tag_ref):
    tag_to_check = tag_ref.name + '-secure'
    try:
        repo.git.rev_parse(tag_to_check)
        return True
    except Exception as e:
        return False

def search_chunk_patching(full_path, vuln_unicode, patched_unicode):
    # takes in file, read as raw, finds the raw chunk of vuln_unicode, replace
    # whole chunk with patched_unicode

    with open(full_path, 'rb') as file:
        raw_data = file.read()

    vuln_bytes = vuln_unicode.encode('utf-8')
    patched_bytes = patched_unicode.encode('utf-8')

    vuln_index = raw_data.find(vuln_bytes)

    if vuln_index != -1:
        # replace
        print("match found!")
        patched_data = raw_data[:vuln_index] + patched_bytes + raw_data[vuln_index + len(vuln_bytes):]
        patched = True
    else:
        print("match not found")
        patched_data=[]
        patched = False
    return patched, patched_data

def process_each_tag(tags_list, repo_path, vuln_unicode, patched_unicode, target_file):
    logger = logging.getLogger('main')
    for tag_ref in tags_list:
        tag_ref_secure = f'{tag_ref}-secure'
        if tag_ref_secure in tags_list:
            logger.info(f"{tag_ref} already has a secure tag, skip this and checkout the secure tag")
            pass
        elif tag_ref == tag_ref_secure:
            logger.info(f"{tag_ref} this is the secure tag to update")
            # since tag is already created, branch was created with
            # the tag, so only check out the branch
            fork.checkout_branch(tag_ref, repo_path)
            file_search_chunk_patching(target_file, vuln_unicode, patched_unicode)
        else:
            print("checkout and create secure")
            logger.info(f"checkout tag and create secure: {tag_ref}")
            fork.check_out_tag(repo_path, tag_ref)
            file_search_chunk_patching(repo_path, target_file, vuln_unicode, patched_unicode, tag_ref)
            
def file_search_chunk_patching(repo_path, target_file, vuln_unicode, patched_unicode, tag_ref):
    logger = logging.getLogger('main')
    print("file searching")
    full_path = repo_path + target_file
    print(full_path)
    print(tag_ref)
    print(vuln_unicode)
    if os.path.exists(full_path):
        logger.info(f"file exists: {full_path}")
        print("file found")
        patched, patched_data = search_chunk_patching(full_path, vuln_unicode, patched_unicode)
        # commit the changes, push to scantist repo, rename original tag
        if patched:
            with open(full_path, 'wb') as file:
                file.write(patched_data)
            print("FILE WRITTEN")
            fork.git_add_commit_push_create_tag(repo_path, full_path, tag_ref)
        else:
            print("patch NOT applied, no new tag")
            pass

def get_json_files(search_code_path: str) -> list[str]:
    json_dir = os.path.join(search_code_path, "json")

    # Check if the json directory exists
    if not os.path.isdir(json_dir):
        logging.error(f"JSON directory does not exist: {json_dir}")
        sys.exit(1)

    return glob.glob(f"{json_dir}/*.json")

def main():
    result: dict = {}
    
    # repo_remote_path = 'https://github.com/codemirror/codemirror5.git' # input
    # repo_remote_path = 'https://github.com/yairEO/tagify.git'
    # repo_remote_path = 'https://github.com/Cacti/cacti.git'
    # repo_remote_path = 'https://github.com/josdejong/jsoneditor.git'
    # repo_remote_path = 'https://github.com/nolimits4web/swiper.git'
    repo_remote_path = 'https://github.com/moment/luxon.git'

    # json filename
    json_filename = 'final_cleaned.json'

    if not os.path.exists('./result'):
        os.makedirs('./result')
    else:
        pass

    for repo_remote_path, relative_filepath, string_to_search in parse_json(json_filename):

        org_name, library_name = get_org_library_names(repo_remote_path)
        repo_name: str = f'result/{org_name}_{library_name}'
        repo_path: str = os.path.join(os.getcwd(), repo_name)

        # relative_filepath = 'mode/javascript/javascript.js' # input
        # relative_filepath = 'src/tagify.js'
        # relative_filepath = 'include/themes/midwinter/main.js'
        # relative_filepath = ''
        # relative_filepath = 'src/utils/utils.js'
        # relative_filepath = 'lib/utils.js'

        # string_to_search = 'if (word == "async" && stream.match(/^(\s|\/\*.*?\*\/)*[\[\(\w]/, false))' # input
        # string_to_search = """_s.placeholder = input.getAttribute('placeholder') || _s.placeholder || """""
        # string_to_search = """$('.import_text').html(fileText);"""
        # string_to_search = """"""
        # string_to_search = r"""const keysArray = Object.keys(Object(nextSource));"""
        # string_to_search = r"""monitor_regex: /^[0-9]{10,11}\.[0-9]+ \[[0-9]+ .+\]( ".+?")+$/,"""



        target_file = os.path.join(repo_path, relative_filepath)

        if not os.path.exists(repo_path) or not os.listdir(repo_path):
            try:
                Repo.clone_from(repo_remote_path, repo_path) # Need the url to clone
            except exc.GitCommandError as e:
                print(f"Git command error: {e}")
        repo: Repo = Repo(repo_path)

        for tag_ref in repo.tags:
            repo.git.checkout(tag_ref.name)
            if os.path.exists(target_file):
                with open(target_file, 'r') as file:
                    result[tag_ref.name] = search_string(file, string_to_search)
        
        # May not need to delete the repo dir after all
        # shutil.rmtree(repo_path)

        counter = 0
        for key, value in result.items():
            if value > 0:
                counter += 1
                print(f"{key}: {value}")

        print(f"{counter}")
        with open(f'{repo_name}.json', 'w') as file:
            json.dump(result, file)


def patch_main():
    logging.basicConfig(level=logging.INFO)
    json_filename = 'final_cleaned.json'

    # include ssh key in environment
    # assuming ssh key is copied to this location
    git_ssh_identity_file = os.path.join(os.getcwd(), 'id_ed25519')
    git_ssh_cmd = f'ssh -i {git_ssh_identity_file}'

    if not os.path.exists('./scantist-ossops'):
        os.makedirs('./scantist-ossops')
    else:
        pass

    for repo_remote_path, relative_filepath, string_to_search, string_to_patch in parse_json_with_patch(json_filename):

        org_name, library_name = get_org_library_names(repo_remote_path)

        fork.fork_repo_to_org(org_name, library_name)

        repo_name: str = f'scantist-ossops/{org_name}_{library_name}'
        repo_path: str = os.path.join(os.getcwd(), repo_name)

        target_file = os.path.join(repo_path, relative_filepath)

        scantist_ossops_remote_path = fork.get_scantist_ossops_remote_path(repo_remote_path, username, password)
        #print(scantist_ossops_remote_path)
        if not os.path.exists(repo_path) or not os.listdir(repo_path):
            try:
                Repo.clone_from(scantist_ossops_remote_path, repo_path, env=dict(GIT_SSH_COMMAND=git_ssh_cmd)) # Need the url to clone
            except exc.GitCommandError as e:
                print(f"Git command error: {e}")
        repo: Repo = Repo(repo_path)
        repo.remotes.origin.fetch(tags=True)
        for tag_ref in repo.tags:
            if check_tag_exists(repo, tag_ref):
                print(f"TAG: {tag_ref.name} already has a secure tag, skipping") 
                pass
            else:
                repo.git.checkout(tag_ref.name)
                print(f"CHECKOUT: {tag_ref.name}")
                if os.path.exists(target_file):
                    print(f"FILE EXISTS: {target_file}")
                    with open(target_file, 'r') as file:
                        patched, patched_lines = search_and_patch(file, string_to_search, string_to_patch)
                    # commit the changes, push to scantist repo, rename original tag
                    temp_branch_name = f'{tag_ref.name}-branch-secure'
                    if patched:
                        # rewrite the file with patched line(s)
                        with open(target_file, 'w') as file:
                            file.writelines(patched_lines)
                        print("FILE IS WRITTEN")
                        push_rename_tag(repo, tag_ref, target_file, temp_branch_name)
                    else:
                        print("PATCH NOT APPLIED, no new tag")
                        pass
        print(f"Delete local file: scantist-ossops/{org_name}_{library_name}")
        folder_path = f'scantist-ossops/{org_name}_{library_name}'
        shutil.rmtree(folder_path)


def curl_patch_main():
    json_filename = 'final_cleaned.json'
    search_code_path = os.getcwd()

    if not os.path.exists('./scantist-ossops'):
        os.makedirs('./scantist-ossops')
    else:
        pass

    for repo_remote_path, relative_filepath, string_to_search, string_to_patch in parse_json_with_patch(json_filename):

        org_name, library_name = get_org_library_names(repo_remote_path)

        fork.fork_repo_to_org(org_name, library_name)

        repo_name: str = f'scantist-ossops/{library_name}'
        repo_path: str = os.path.join(os.getcwd(), repo_name)

        target_file = os.path.join(repo_path, relative_filepath)

        if not os.path.exists(repo_path) or not os.listdir(repo_path):
            fork.clone_scantist_repo(library_name)
        else:
            print("repo is already cloned")
            pass

        tags_list = fork.get_all_tags(org_name, library_name)
        for tag_ref in tags_list:
            tag_ref_secure = f'{tag_ref}-secure'
            if "-secure" in tag_ref or tag_ref_secure in tags_list:
                print(f"TAG: {tag_ref} already has a secure tag, skipping") 
                pass
            else:
                print(f"CHECKOUT: {tag_ref}")
                fork.check_out_tag(repo_path, tag_ref)
                if os.path.exists(target_file):
                    print(f"FILE EXISTS: {target_file}")
                    with open(target_file, 'r') as file:
                        patched, patched_lines = search_and_patch(file, string_to_search, string_to_patch)
                    # commit the changes, push to scantist repo, rename original tag
                    if patched:
                        # rewrite the file with patched line(s)
                        with open(target_file, 'w') as file:
                            file.writelines(patched_lines)
                        print("FILE IS WRITTEN")
                        fork.git_add_commit_push_create_tag(repo_path, target_file, tag_ref)
                    else:
                        print("patch NOT applied, no new tag")
                        pass
        print(f"Delete local file: scantist-ossops/{library_name}")
        folder_path = f'scantist-ossops/{library_name}'
        os.chdir(search_code_path)
        shutil.rmtree(folder_path)
    print("Getting secure tag counts")
    secure_tag_counts = fork.get_secured_tag_counts()
    print(f"Secure tag counts: {secure_tag_counts}")


def chunk_patch_curl_main():
    logger = logging.getLogger('main')

    search_code_path = os.getcwd()

    json_files = get_json_files(search_code_path)

    if not os.path.exists('./scantist-ossops'):
        os.makedirs('./scantist-ossops')

    for json_file in json_files:
        for git_url_list, relative_filepath, vuln_unicode, patched_unicode in fork.parse_patchhunk_json(json_file):
            for git_url in git_url_list:
                org_name, library_name = fork.get_org_library_name(git_url)
                repo_exist = fork.fork_repo_to_org(org_name, library_name)
                if repo_exist:
                    repo_name: str = f'scantist-ossops/{library_name}'
                    repo_path: str = os.path.join(os.getcwd(), repo_name)

                    target_file = os.path.join(repo_path, relative_filepath)

                    if not os.path.exists(repo_path) or not os.listdir(repo_path):
                        fork.clone_scantist_repo(library_name)
                    else:
                        print("no clone")
                        logger.info("repo is already cloned")
                        # fork.update_forked_repo(repo_path, git_url)

                    tags_list = fork.get_all_tags(org_name, library_name)
                    process_each_tag(tags_list, repo_path, vuln_unicode, patched_unicode, target_file)

                    print(f"Delete local file: scantist-ossops/{library_name}")
                    folder_path = f'scantist-ossops/{library_name}'
                    os.chdir(search_code_path)
                    shutil.rmtree(folder_path)
                else:
                    continue
                print("Getting secure tag counts")
                secure_tag_counts = fork.get_secured_tag_counts()
                logger.info(f"Secure tag counts: {secure_tag_counts}")
                print(f"Secure tag counts: {secure_tag_counts}")




if __name__ == '__main__':
    start_log()
    chunk_patch_curl_main()