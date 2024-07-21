from github import Github
from github import Auth
from github import Commit, Branch, PullRequest, PaginatedList
import datetime

class GHMaster:

    def __init__(self, token, repo_name) -> None:
        self.repo = self.get_repo(token, repo_name)

    def get_repo(self, token:str, repo_name:str):
        github = Github(auth=Auth.Token(token))
        repo = github.get_repo(repo_name)
        if repo is None:
            print(f'wrong repo name: {repo_name}')
        else:
            return repo
    

class Commiter(GHMaster):

    def __init__(self, token, repo_name) -> None:
        super().__init__(token, repo_name)


    def get_commits(self) -> list:
        commits =  self.repo.get_commits()
        self.num_commits = commits.totalCount
        return commits
    
    def get_day_commits(self, date:datetime.date) -> PaginatedList:
        commits =  self.repo.get_commits(since=date)
        #self.num_commits = commits.totalCount
        return commits

    def get_commit(self, sha:str) -> Commit:
        return self.repo.get_commit(sha=sha)
    

class Branchar(GHMaster):

    def __init__(self, token, repo_name) -> None:
        super().__init__(token, repo_name)

    def get_branch_list(self) -> list:
        pass

    def get_branch(self) -> Branch:
        pass


class PullRequester(GHMaster):

    def __init__(self, token, repo_name) -> None:
        super().__init__(token, repo_name)

    def get_pull_request_list(self) -> list:
        pass

    def get_pull_request(self) -> PullRequest:
        pass

