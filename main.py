from git import Repo, exc
import logging
import os
# import shutil
import json
import ast

logging.basicConfig(level=logging.INFO)

def search_string(file, string_to_search):
    count = 0
    for line in file:
        if string_to_search in line:
            print("Exact match found.")
            count += 1
    return count

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
    for repo_remote_path, relative_filepath, string_to_search in parse_json(json_filename):

        org_name, library_name = get_org_library_names(repo_remote_path)
        repo_name: str = f'{org_name}_{library_name}'
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

if __name__ == '__main__':
    main()