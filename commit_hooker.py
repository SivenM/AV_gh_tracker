import os
import yaml
import github_api
import datetime
import time
import argparse
import utils
from tg_app import TgBot
from github import Commit, PaginatedList


class Hooker:
    def __init__(self, token:str, repo_name:str, out=None) -> None:
        self.commiter = github_api.Commiter(token, repo_name)
        self.outer = out
        self.commits_count = 0
        self.cache = []
        self.date = None
        self.history_dir = 'history'
        utils.mkdir(self.history_dir)

    def update_date(self) -> datetime.date:
        current_date = datetime.datetime.now().date()
        #if self.date == None or self.date != current_date:
        #    self.date = current_date
        return current_date

    def hook_commits(self, date:datetime.date) -> PaginatedList:
        return self.commiter.get_day_commits(date)

    def check_diff_count(self, count:int) -> int:
        diff = count - self.commits_count
        return diff

    def extruct_commit_data(self, commit:Commit) -> dict:
        return  {
            'date': commit.commit.author.date,
            'author': commit.commit.author.name,
            'hash': commit.commit.sha
        }

    def message(self, commit_data:dict, text=None) -> None:
        if text is None:
            text = f"New commit at {commit_data['date']}:\n\tcommit author: {commit_data['author']}\n\tcommit hash: {commit_data['hash']}"

        if self.outer:
            self.outer.send_message(text)
        else:
            print(text)

    def save_cache(self, date:datetime.date) -> None:
        save_path = os.path.join(self.history_dir, 'commits_' + date.strftime('%d-%m-%Y') + '.json')
        utils.save_json(self.cache, save_path)

    def tarck_commits(self):
        date = datetime.datetime.now().date()
        while True:
            date = self.update_date()
            commits = self.hook_commits(date)
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
    bot = TgBot(config['tg_token'], config['channel_login'])
    hooker = Hooker(config['gh_token'], config['repo_name'], bot)
    hooker.tarck_commits()


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