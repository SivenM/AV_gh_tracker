import yaml


def load_yaml(path:str) -> dict|list:
    with open(path) as f:
        templates = yaml.safe_load(f)
    return templates