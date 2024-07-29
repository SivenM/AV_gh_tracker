import argparse
import telebot


class TgBot:
    def __init__(self, token:str, chat_id=str) -> None:
        self.bot = telebot.TeleBot(token)
        self.chat_id=chat_id

    def send_message(self, text:str):
        self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode='Markdown', disable_web_page_preview=True)