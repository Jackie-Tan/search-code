from git import Repo, exc
import logging
import os

logging.basicConfig(level=logging.DEBUG)

def main():
    cwd = os.getcwd()
    repo_path = os.path.join(cwd, 'test')
    if not os.path.exists(repo_path) or not os.listdir(repo_path):
        try:
            Repo.clone_from('https://github.com/pimcore/pimcore.git', repo_path) # Need the url to clone
        except exc.GitCommandError as e:
            print(f"Git command error: {e}")
    repo = Repo(repo_path)
    tags_with_timestamps = {}
    for tag_ref in repo.tags:
        commit = tag_ref.commit
        tags_with_timestamps[tag_ref.name] = commit.authored_datetime

    for tag, timestamp in tags_with_timestamps.items():
        print(f"Tag: {tag}, Timestamp: {timestamp}")

if __name__ == '__main__':
    main()