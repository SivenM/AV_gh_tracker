import os
import yaml
import github_api
import datetime
import time
import argparse
import utils
import pytz
from tg_app import TgBot
from github import Commit, PaginatedList, PullRequest


class Tracker:
    def __init__(self, token:str, repo_name:str, out=None, sleep:int=30) -> None:
        self.pler = github_api.PullRequester(token, repo_name)
        self.outer = out
        self.commits_count = 0
        self.cache = []
        self.timezone = pytz.UTC#pytz.timezone('Europe/Moscow')
        self.date = self.get_current_date()
        self.history_dir = 'history'
        utils.mkdir(self.history_dir)
        self.sleep = sleep
        self.commit_info_form = "New commit at {}:\n\tcommit author: {}\n\tcommit hash: {}\n{}\n"

    def get_current_date(self) -> datetime.date:
        current_date = datetime.datetime.now().date()
        current_date = datetime.datetime.combine(current_date, datetime.datetime.min.time())
        #if self.date == None or self.date != current_date:
        #    self.date = current_date
        return current_date.replace(tzinfo=self.timezone)

    def check_new_date(self):
        new_current_day = datetime.date.today()
        if new_current_day == self.date.date():
            self.save_cache()
            self.cache = []


    def update_date(self, pls:PullRequest):
        if pls[0].updated_at > self.date:
            self.date = pls[0].updated_at

    def hook_commits(self, date:datetime.date) -> PaginatedList:
        return self.commiter.get_day_commits(date)

    def check_diff_count(self, count:int) -> int:
        diff = count - self.commits_count
        return diff

    def extruct_commit_data(self, commit:Commit) -> dict:
        return  {
            'date': commit.commit.author.date.isoformat(),
            'author': commit.commit.author.name,
            'hash': commit.commit.sha
        }

    def get_commits_from_pl(self, pl:PullRequest) ->list:
        out = []
        pl_commits = list(pl.get_commits())[::-1]
        if len(pl_commits) > 0:
            el = 0
            getting = True
            while getting:
                commit = pl_commits[el]
                if commit.commit.author.date >= self.date:
                    extructed_data = self.extruct_commit_data(commit)
                    out.append(extructed_data)
                    el += 1
                else:
                    getting = False
        return out

    def get_current_commits(self, pls:list) -> list:
        commit_list = []
        for pl in pls:
            commits = self.get_commits_from_pl(pl)
            commit_list += commits
        return commit_list
    
    def message(self, commit_data:dict, text:str=None) -> None:
        if text is None:
            text = f"New commit at {commit_data['date']}:\n\tcommit author: {commit_data['author']}\n\tcommit hash: {commit_data['hash']}"

        if self.outer:
            self.outer.send_message(text)
        else:
            print(text)

    def send_commits_info(self, commits:list, form:str=None) -> None:
        if form is None:
            form = self.commit_info_form
        
        text = 'Commit info.\n'
        for commit in commits:
            text += form.format(commit['date'], commit['author'], commit['hash'], '='*80)
        
        if self.outer:
            self.outer.send_commits_info(text)
        else:
            print(text)

    def save_cache(self) -> None:
        save_path = os.path.join(self.history_dir, 'commits_' + self.date.strftime('%d-%m-%Y') + '.json')
        utils.save_json(self.cache, save_path)

    def track(self):
        while True:
            self.check_new_date()
            pls = self.pler.get_pull_request_list(date=self.date)
            if len(pls) > 0:
                commits = self.get_current_commits(pls)
                self.update_date(pls)
                if len(commits) > 0:
                    self.send_commits_info(commits)
                    self.cache += commits
                    self.save_cache()
            time.sleep(self.sleep)

    def tarck_commits(self): #to trash
        while True:
            date = self.update_date()
            commits = self.hook_commits(date)
            print(f'Количество коммитов за {date.date().strftime("%d:%m:%Y")}: {commits.totalCount}')
            diff_count = self.check_diff_count(commits.totalCount)
            if diff_count > 0:
                self.commits_count = commits.totalCount
                for commit in commits[:diff_count]:
                    commit_data = self.extruct_commit_data(commit)
                    self.message(commit_data)
                    self.cache.append(commit_data)
                    self.save_cache()
            time.sleep(30)


def let_hook(config:dict) -> None:
    print('start tracking')
    bot = TgBot(config['tg_token'], config['channel_login'])
    tracker = Tracker(config['gh_token'], config['repo_name'], bot)
    tracker.track()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='Ловит коммиты за текущий день и собирает инфу по ним')
    parser.add_argument('-c', '--config', dest='config', type=argparse.FileType('r'), default=None)
    args = parser.parse_args()
    if args.config:
        try:
            config = yaml.safe_load(args.config)
            let_hook(config)
        except FileNotFoundError:
            print(f'Файл {args.config} не найден')
        except yaml.YAMLError as exc:
            print(f'Ошибка при чтении YAML файла: {exc}')