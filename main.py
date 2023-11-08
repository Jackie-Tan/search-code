from git import Repo, exc
import logging
import os
import shutil
import json

logging.basicConfig(level=logging.INFO)

def search_string(file, string_to_search):
    count = 0
    for line in file:
        if string_to_search in line:
            print("Exact match found.")
            count += 1
    return count

def main():
    result: dict = {}
    cwd: str = os.getcwd()
    repo_path: str = os.path.join(cwd, 'test')
    # repo_remote_path = 'https://github.com/codemirror/codemirror5.git' # we need
    repo_remote_path = 'https://github.com/yairEO/tagify.git'
    # relative_filepath = 'mode/javascript/javascript.js' # we need
    relative_filepath = 'src/tagify.js' 
    # string_to_search = 'if (word == "async" && stream.match(/^(\s|\/\*.*?\*\/)*[\[\(\w]/, false))' # we need
    string_to_search = """_s.placeholder = input.getAttribute('placeholder') || _s.placeholder || """""
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
    
    shutil.rmtree(repo_path)
    counter = 0
    for key, value in result.items():
        if value > 0:
            counter += 1
            print(f"{key}: {value}")

    print(f"{counter}")
    with open('tagify.json', 'w') as file:
        json.dump(result, file)
    # tags_with_timestamps = {}
    # for tag_ref in repo.tags:
    #     commit = tag_ref.commit
    #     tags_with_timestamps[tag_ref.name] = commit.authored_datetime

    # for tag, timestamp in tags_with_timestamps.items():
    #     print(f"Tag: {tag}, Timestamp: {timestamp}")

if __name__ == '__main__':
    main()