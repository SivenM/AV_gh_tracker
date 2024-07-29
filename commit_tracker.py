from typing import Optional
import os
import yaml
import github_api
from pydantic import BaseModel
import datetime
import time
import argparse
import utils
import pytz
from tg_app import TgBot
from github import Commit, PaginatedList, PullRequest
from loguru import logger


class CommitData(BaseModel):
    date:str
    author:str
    hash:str
    num_lines:int
    num_files:int
    delta_day:Optional[float]
    delta_pl:Optional[float]
    message:str
    url:str
    pl_url:str
    

class Cache:

    def __init__(self, history_dir:str) -> None:
        self.history_dir = history_dir
        self.commits_lake = []
        self.authors_dates = {}

    def get(self, data:list) -> None:
        if len(data) > 0:
            for commit in data:
                author = commit.author
                date = datetime.datetime.fromisoformat(commit.date)
                if author in self.authors_dates:
                    self.authors_dates[author].append(date)
                else:
                    self.authors_dates[author] = [date]
    
                self.commits_lake.append(commit)

    def save(self, date) -> None:
        save_data = list(map(lambda x: x.model_dump(), self.commits_lake))
        save_path = os.path.join(self.history_dir, 'commits_' + date.strftime('%d-%m-%Y') + '.json')
        utils.save_json(save_data, save_path)
        logger.info(f"cache saved in {save_path}")

    def clear(self) -> None:
        self.commits_lake = []
        self.authors_dates = {}
        logger.info("cache cleared!")

    def set_author_last_date(self, author:str) -> list:
        if author in self.authors_dates:
            return self.authors_dates[author][-1]
        else:
            return None


class FeatureCreator:

    def __init__(self) -> None:
        pass

    def create_num_lines_files(self,  commit:Commit) -> int:
        files = list(commit.files)
        num_files = len(files)
        count_line = 0
        for file in files:
            diff = file.patch
            for diff_line in diff.splitlines():
                    if diff_line[0] == '+' and not diff_line[:3] == "+++" and diff_line != '-':
                        count_line += 1
        return count_line, num_files

    def _create_delta(self, curr_day:datetime.datetime, prev_commit_date:datetime.datetime) -> float:
        return (curr_day - prev_commit_date).total_seconds()

    def create_delta_day(self, commit_date:datetime.datetime, author_last_date:datetime):
        if author_last_date == None:
            delta_day = 0.
        else:
            delta_day = self._create_delta(commit_date, author_last_date)
        return delta_day

    def create_delta_pl(self, commit_date:datetime.datetime, prev_commit:datetime.datetime):
        if prev_commit == None:
            delta_pl = 0.
        else:
            delta_pl = self._create_delta(commit_date, prev_commit)
        return delta_pl

    def create_features(self, commit:Commit, prev_commit_pl:Commit=None, prev_date_author:datetime.datetime=None, pl_url:str=None) -> CommitData:
        num_lines, num_files = self.create_num_lines_files(commit)
        return CommitData(
            date=commit.commit.author.date.isoformat(),
            author=commit.commit.author.name,
            hash=commit.commit.sha,
            message=commit.commit.message,
            url=commit.html_url,
            pl_url=pl_url,
            num_lines=num_lines,
            num_files=num_files,
            delta_day=self.create_delta_day(commit.commit.author.date, prev_date_author),
            delta_pl=self.create_delta_pl(commit.commit.author.date, prev_commit_pl)
        )


class TimeHandler:

    def __init__(self) -> None:
        self.timezone = pytz.UTC

    def get_current_date(self) -> datetime.date:
        current_date = datetime.datetime.now().date()
        current_date = datetime.datetime.combine(current_date, datetime.datetime.min.time())
        return current_date.replace(tzinfo=self.timezone)

    def is_new_date(self, date:datetime.date):
        new_current_day = datetime.date.today()
        if new_current_day == date.date():
            return False
        else:
            return True

    def update_date(self, date:datetime.date, pls:PullRequest):
        if len(pls) == 0:
            return date
        
        pls_dates = list(map(lambda x: x.updated_at, pls))
        max_date  = max(pls_dates)
        if max_date > date:
            return max_date
        else:
            return date
            

class Messanger:

    def __init__(self, outer=None) -> None:
        self.outer = outer
        self.commit_info_form = "New commit:\n\n{}\n\n\tdate: {}\n\tcommit author: {}\n\tcommit hash: {}" + \
            "\n\tnum lines: {}\n\tnum files: {}\n\tpl delta: {}\n\tauthor delta: {}" + \
            "\n\n[commit link]({})\n[pull request link]({})\n" + "_"*10 + "\n"
            #'\n\n<a href="{}"commit link</a>\n<a href="{}"pull request link</a>\n' + "_"*10 + "\n"
    
    def message(self, text:str=None) -> None:
        if self.outer:
            self.outer.send_message(text)
        else:
            print(text)

    def send_commits_info(self, commits:CommitData, form:str=None) -> None:
        if form is None:
            form = self.commit_info_form
        
        if len(commits) > 8:
            text = f"detected {len(commits)}. see history date fro details"
        else:
            text = 'Commit info.\n'
            for commit in commits:
                text += form.format(
                    commit.message, 
                    commit.date, 
                    commit.author, 
                    commit.hash, 
                    commit.num_lines, 
                    commit.num_files, 
                    commit.delta_pl, 
                    commit.delta_day, 
                    commit.url, 
                    commit.pl_url
                    )
        
        if self.outer:
            self.outer.send_message(text)
            logger.info(f"message sended in tg")
        else:
            print(text)


class Tracker:

    def __init__(self, token:str, repo_name:str, out=None, sleep:int=30, history_dir='history') -> None:
        self.pler = github_api.PullRequester(token, repo_name)
        self.time_handler = TimeHandler()
        self.messanger = Messanger(out)
        self.fcreator = FeatureCreator()
        self.cache = Cache(history_dir)

        self.commits_count = 0
        self.date = self.time_handler.get_current_date()
        self.history_dir = 'history'
        utils.mkdir(self.history_dir)
        self.sleep = sleep

    def hook_commits(self, date:datetime.date) -> PaginatedList:
        return self.commiter.get_day_commits(date)

    def check_diff_count(self, count:int) -> int:
        diff = count - self.commits_count
        return diff

    def get_prev_commit(self, el:int, commits:list) -> Commit:
        next_el = el + 1
        if next_el >= len(commits):
            return None
        else:
            return commits[next_el]

    def get_commits_from_pl(self, pl:PullRequest) ->list:
        out = []

        pl_commits = list(pl.get_commits())[::-1]
        num_commits = len(pl_commits)

        if len(pl_commits) > 0:
            el = 0
            getting = True
            while getting:
                if el == num_commits:
                    getting = False
                else: 
                    commit = pl_commits[el]
                    if commit.commit.author.date >= self.date:
                        prev_commit_pl = self.get_prev_commit(el, pl_commits)
                        prev_date_author = self.cache.set_author_last_date(commit.commit.author.name)
                        commit_data = self.fcreator.create_features(commit, prev_commit_pl, prev_date_author, pl.html_url)
                        out.append(commit_data)
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

    def track(self):
        logger.info(f"start tracking at {self.date}")
        while True:
            #check new day
            check = self.time_handler.is_new_date(self.date)
            if check:
                self.cache.save(self.date)
                self.cache.clear()
                self.date = self.time_handler.get_current_date()
            #get data    
            pls = self.pler.get_pull_request_list(date=self.date)
            logger.info(f"get {len(pls)} pls")
            if len(pls) > 0:
                commits = self.get_current_commits(pls)
                self.date = self.time_handler.update_date(self.date, pls)
                logger.info(f"date updated to {self.date}")
                logger.info(f"get {len(commits)} commits")
                if len(commits) > 0:
                    self.messanger.send_commits_info(commits)
                    self.cache.get(commits)
                    self.cache.save(self.date)
            time.sleep(self.sleep)


def let_hook(config:dict) -> None:
    print('start tracking')
    if type(config['tg_token']) == str or len(config['tg_token']) > 0:
        bot = TgBot(config['tg_token'], config['channel_login'])
    else:
        bot = None
    tracker = Tracker(config['gh_token'], config['repo_name'], bot)
    tracker.track()


if __name__ == '__main__':
    logger.add("logs/info.log", format="{time} {level} {message}", level="INFO", rotation='00:00', compression="zip")
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