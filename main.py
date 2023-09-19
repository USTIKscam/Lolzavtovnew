import os
import re
import time
import json
import random
import ctypes
import traceback

import requests
from loguru import logger


def set_title():
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW('[AutoLolz v4] by @its_niks - https://zelenka.guru/members/3870999/')

with open('config.json') as file:
    config = json.load(file)
    if config['thread_url'] == '' or config['lolz_token'] == '':
        logger.error('Ошибка, заполните config.json')
        input()
        raise SystemExit()

with open('data.txt', 'r', encoding='utf-8') as file:
    keys = file.readlines()
    if len(keys) == 0:
        logger.error('Ошибка, заполните data.txt')
        input()
        raise SystemExit()

def save_replied_users(data):
    with open('replied_users.json', 'w', encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4))

def save_keys(data):
    with open('data.txt', 'w', encoding="utf-8") as f:
        f.write(''.join(data))

if input('Вы хотите начать раздачу с начала темы(очистка replied_users.json)? (y/n): ').lower() == 'y':
    with open('replied_users.json', 'w', encoding="utf-8") as f:
        data = {}
        f.write(json.dumps(data, indent=4))
        logger.info('replied_users.json был успешно очищен.')

with open('replied_users.json', 'r', encoding="utf-8") as f:
    sent_messages = json.load(f)

delay = config['delay']
lolz_token = config['lolz_token']
data_count = config["data_count"]
api_domain = config["api_domain"]

class Lolz:
    def __init__(self, token):
        self.sess = requests.Session()
        self.sess.headers = {
            'Authorization': f'Bearer {token}',
            }

        self.thread_url = config["thread_url"]
        match = re.search('https?://(lolz|zelenka)\.guru/threads/(\d+)/?', config["thread_url"])
        if not match:
            logger.error(f'Unexpected thread URL format: {config["thread_url"]}')
            input()
            raise SystemExit()
        self.thread_id = match.group(2)
        if config['proxy'] != '':
            proxy_dict = {
                "http":config['proxy'],
                "https":config['proxy'],
            }
            self.sess.proxies.update(proxy_dict)

    def check_user(self):
        response = self.sess.get(f'https://{api_domain}/forums').json()
        if 'forums' not in response.keys():
            return False
        return True

    def get_posts(self):
        with open('replied_users.json', 'r', encoding="utf-8") as f:
            sent_messages = json.load(f)
        all_posts = []
        r = self.sess.get(f"https://{api_domain}/posts?thread_id={self.thread_id}")
        try:
            r = r.json()
        except:
            logger.error(f'Ошибка доступа к API.')
            logger.error(r.text)
            time.sleep(15)
            return
        try:
            all_pages = r["links"]['pages']
        except KeyError:
            all_pages = 1
        logger.info(f'Найдено {all_pages} страниц(-ы) с новыми постами')
        author_username = r["thread"]["creator_username"]
        time.sleep(6)
        for i in range(1 if len(sent_messages) == 0 else list(sent_messages.values())[-1], all_pages+1):
            r = self.sess.get(f"https://{api_domain}/posts?thread_id={self.thread_id}&page={i}")
            try:
                page = r.json()
            except:
                logger.error(f'Ошибка доступа к API.')
                logger.error(r.text)
                break
            posts = page["posts"]
            for post in posts:
                if str(post["post_id"]) not in sent_messages:
                    if post["poster_username"] != author_username:
                        all_posts.append({'post_id': post["post_id"], 'author' : post["poster_username"], 'author_id' : post["poster_user_id"], 'page' : i, 'text' : post["post_body"]})
            time.sleep(6)
        return all_posts

    def post_comment(self, post_id, username, user_id,  text):
        data = {
            "comment_body" : f'[USERIDS={user_id}]@{username}, {text}[/USERIDS]',
            }
        r = self.sess.post(f'https://{api_domain}/posts/{post_id}/comments', data=data)
        try:
            response = r.json()
            if 'comment' in response.keys():
                return True
            else:
                return response
        except:
            logger.error(f'Ошибка доступа к API.')
            logger.error(r.text)

def distribution(lzt, keys):
    if config['dynamic_data']:
        with open('data.txt', 'r', encoding='utf-8') as file:
            keys = file.readlines()
            if len(keys) == 0:
                logger.error('Ожидаю новые ключи...')
                time.sleep(10)
                return
    logger.info('Произвожу парсинг...')
    posts = lzt.get_posts()
    if posts is None:
        time.sleep(random.randrange(delay[0], delay[1]))
        return
    if len(posts) == 0:
        logger.info(f'Ожидаю новые сообщения')
        time.sleep(random.randrange(delay[0], delay[1]))
    else:
        logger.info(f'Найдено {len(posts)} сообщений.')
        for post in posts:
            if len(keys) == 0:
                if config['dynamic_data']:
                    logger.error('Ожидаю новые ключи...')
                    time.sleep(10)
                    return
                else:
                    logger.error('Закончились ключи. Нажмите на любую кнопку, чтобы завершить...')
                    input()
                    raise SystemExit()
            prize = '\n'
            for i in range(data_count):
                try:
                    prize += f'{keys[0].strip()}\n'
                    keys.remove(keys[0])
                except IndexError:
                    prize += ''
            comment_status = lzt.post_comment(post["post_id"], post['author'], post['author_id'], prize)
            if comment_status:
                sent_messages[post["post_id"]] = post["page"]
                save_replied_users(sent_messages)
                save_keys(keys)
                logger.success(f'Сообщение {post["author"]} было прокомментировано.')

            else:
                logger.info(comment_status)
                logger.error(f'Ошибка при комментировании сообщения {post["author"]}')

            time.sleep(random.randrange(delay[0], delay[1]))


def main(keys):
    set_title()
    lzt = Lolz(lolz_token)
    if lzt.check_user():
        time.sleep(5)
        while True:
            try:
                distribution(lzt, keys)
            except Exception as ex:
                logger.error(traceback.format_exc())
                time.sleep(random.randrange(delay[0], delay[1]))
    else:
        logger.error(f'Invalid Token')
        input()
        raise SystemExit()

main(keys)
