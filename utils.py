import os
import yaml
import json


def load_yaml(path:str) -> dict|list:
    with open(path) as f:
        templates = yaml.safe_load(f)
    return templates


def load_json(path:str) -> dict|list:
    with open(path, 'rb') as read_file:
        ann = json.load(read_file)
    return ann


def save_json(data, save_path, desc=None):
    with open(save_path, "w", encoding="utf8") as write_file:
        json.dump(data, write_file, ensure_ascii=False)
        if desc:
            print(desc)


def mkdir(path:str) -> None:
    if os.path.exists(path) == False:
        os.mkdir(path)