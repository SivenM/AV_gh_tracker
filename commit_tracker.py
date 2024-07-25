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
from loguru import logger


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
        if pls[0].updated_at > date:
            return pls[0].updated_at
        else:
            return date
            

class Messanger:

    def __init__(self, outer=None) -> None:
        self.outer = outer
        self.commit_info_form = "New commit:\n\n{}\n\n\tdate: {}\n\tcommit author: {}\n\tcommit hash: {}\n\n" + \
            "[commit link]({})\n[pull request link]({})" + "_"*10 + "\n"
    
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
        
        if len(commits) > 10:
            text = f"detected {len(commits)}. see cache date fro details"
        else:
            text = 'Commit info.\n'
            for commit in commits:
                text += form.format(commit['message'], commit['date'], commit['author'], commit['hash'], commit['url'], commit['pl_url'])
        
        if self.outer:
            self.outer.send_message(text)
            logger.info(f"message sended in tg")
        else:
            print(text)


class Tracker:

    def __init__(self, token:str, repo_name:str, out=None, sleep:int=30) -> None:
        self.pler = github_api.PullRequester(token, repo_name)
        self.time_handler = TimeHandler()
        self.messanger = Messanger(out)

        self.commits_count = 0
        self.cache = []
        self.date = self.time_handler.get_current_date()
        self.history_dir = 'history'
        utils.mkdir(self.history_dir)
        self.sleep = sleep

    def hook_commits(self, date:datetime.date) -> PaginatedList:
        return self.commiter.get_day_commits(date)

    def check_diff_count(self, count:int) -> int:
        diff = count - self.commits_count
        return diff

    def extruct_commit_data(self, commit:Commit) -> dict:
        return  {
            'date': commit.commit.author.date.isoformat(),
            'author': commit.commit.author.name,
            'hash': commit.commit.sha,
            'message': commit.commit.message,
            'url': commit.url
        }

    def get_commits_from_pl(self, pl:PullRequest) ->list:
        out = []
        pl_commits = list(pl.get_commits())[::-1]
        num_commits = len(pl_commits)

        if len(pl_commits) > 0:
            el = 0
            getting = True
            while getting:
                if el == num_commits:
                    return out 
                commit = pl_commits[el]
                if commit.commit.author.date >= self.date:
                    extructed_data = self.extruct_commit_data(commit)
                    extructed_data['pl_url'] = pl.url
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

    def save_cache(self) -> None:
        save_path = os.path.join(self.history_dir, 'commits_' + self.date.strftime('%d-%m-%Y') + '.json')
        utils.save_json(self.cache, save_path)
        logger.info(f"cache saved in {save_path}")

    def track(self):
        logger.info(f"start tracking at {self.date}")
        while True:
            #check new day
            out = self.time_handler.is_new_date(self.date)
            if out:
                self.save_cache()
                self.cache = []
                self.date = self.time_handler.get_current_date()
                logger.info("cache cleared!")
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