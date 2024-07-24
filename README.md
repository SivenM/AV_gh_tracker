# AV github tracking

Скрипты для трекинга, аналитики данных через github api.

## Установка зависимостей

```
pip install -r requirements.txt
```

## Запуск

```
python commit_tracker.py -c cfg.yaml
```

__cfg.yaml__ состоит из следующих параметров:
```yaml
gh_token: "aaaaaaaa"
repo_name: "bbb/bbb"
tg_token: "ccccccc"
channel_login: "@chat"

```