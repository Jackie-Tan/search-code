from git import Repo, exc
import logging
import os
# import shutil
import json
import ast
import fork

logging.basicConfig(level=logging.INFO)

def search_string(file, string_to_search):
    count = 0
    for line in file:
        if string_to_search in line:
            print("Exact match found.")
            count += 1
    return count

def search_and_patch(file, string_to_search, string_to_patch):
    patched_lines = []
    for line in file:
        if string_to_search in line:
            patched_lines.append(line.replace(string_to_search, string_to_patch))
        else:
            patched_lines.append(line)
    return patched_lines


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
            except:
                string_to_search = '=============+++++++++++++++==============----------------'
            try:
                string_to_patch = string_to_search_dict[relative_filepath]['+'][0]
            except:
                string_to_patch = '=============+++++++++++++++==============----------------'
            yield (repo_remote_path, relative_filepath, string_to_search, string_to_patch)

def push_rename_tag(repo, tag_ref, file_to_add):
    new_tag_name = tag_ref.name + '-secure'
    commit_message = "Patch vulnerability in older version"
    try:
        # first push all file changes
        repo.index.add([file_to_add])
        repo.index.commit(commit_message)
        repo.remotes.origin.push(tag_ref.name)
        # create a new local tag from old tag, delete local tag and push new to
        # remote, delete old tag on origin
        repo.create_tag(new_tag_name, ref=tag_ref.commit)
        print(f"delete {tag_ref.name}")
        repo.delete(tag_ref.name)
        print(f"new tag {new_tag_name}")
        repo.remotes.origin.push(new_tag_name)
    except Exception as e:
        print(f"Error: {e}")
    input("CHECK THE TAGS AND EVERYTHING IN GITHUB FIRST")

def main():
    result: dict = {}
    
    # repo_remote_path = 'https://github.com/codemirror/codemirror5.git' # input
    # repo_remote_path = 'https://github.com/yairEO/tagify.git'
    # repo_remote_path = 'https://github.com/Cacti/cacti.git'
    # repo_remote_path = 'https://github.com/josdejong/jsoneditor.git'
    # repo_remote_path = 'https://github.com/nolimits4web/swiper.git'
    repo_remote_path = 'https://github.com/NodeRedis/node-redis.git'

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
    json_filename = 'final_cleaned.json'

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

        scantist_ossops_remote_path = fork.get_scantist_ossops_remote_path(repo_remote_path)

        if not os.path.exists(repo_path) or not os.listdir(repo_path):
            try:
                Repo.clone_from(scantist_ossops_remote_path, repo_path) # Need the url to clone
            except exc.GitCommandError as e:
                print(f"Git command error: {e}")
        repo: Repo = Repo(repo_path)

        for tag_ref in repo.tags:
            repo.git.checkout(tag_ref.name)
            if os.path.exists(target_file):
                with open(target_file, 'r') as file:
                    patched_lines = search_and_patch(file, string_to_search, string_to_patch)
                # rewrite the file with patched line(s)
                with open(target_file, 'w') as file:
                    file.writelines(patched_lines)
                
                # commit the changes, push to scantist repo, rename original tag
                push_rename_tag(repo, tag_ref, target_file)
                

if __name__ == '__main__':
    patch_main()