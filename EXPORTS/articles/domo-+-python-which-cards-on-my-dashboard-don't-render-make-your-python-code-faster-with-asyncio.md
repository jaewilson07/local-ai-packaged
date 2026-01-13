---
title: "Domo + Python - Which cards on my dashboard don't render?  Make your Python Code faster with Asyncio"
url: /c/developerdomocom-community-edition/domo-python-which-cards-on-my-dashboard-don-t-render-make-your-python-code-faster-with-asyncio
author: Jae Myong Wilson
published_date: Aug 12, 2022
updated_date: Nov 26, 2022 at 10:59 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# Domo + Python - Which cards on my dashboard don't render?  Make your Python Code faster with Asyncio
**Author:** Jae Myong Wilson
**Published:** Aug 12, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

﻿

﻿
"For each card on my page (or instance), report if the card will render or not."

Do you have API [#automations](https://www.youtube.com/hashtag/automations) that take hours to run?

When you query [#APIs](https://www.youtube.com/hashtag/apis) sequentially, code runtime increases linearly with the number of requests.  [#Python](https://www.youtube.com/hashtag/python) [#asyncio](https://www.youtube.com/hashtag/asyncio) library allows your code to run [#asynchronously](https://www.youtube.com/hashtag/asynchronously).

Asyncio KB - [https://docs.python.org/3/library/asy...](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqa3k5dHc1VVc4eURXVlh2Z2JXellkOE9oNWRSd3xBQ3Jtc0tsanV5U2NoTnB2NndFRnAyWkxUMGtWemhsd3p4UlRmSEJ3cktXQlQxU1hXcnVkTmxLb3Y4bUNLbm5lSjZjcXVpSEZta3NlSUhIcTFOcDd2bVlKNHJtaUxyRGVxcW8zUkJvd3hZLUo3end1UjZaaXFkOA&q=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Fasyncio.html&v=3ZwlzOlRBbA)
Aiohttp KB - [https://pypi.org/project/aiohttp/](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqbERRcUY1TVFFMWVEMUY5aFVCeDRNSnM4RS1TZ3xBQ3Jtc0tuNHdfTm04RWFDZnYtT3ZNYmtpVmhtMHNFSTZBdXl2ckJndTZ2LWpDZGRKeGJid3BHa1JuY3RtbFlCck9GWEZXbVNRZTlsZHozZG1qQWNTMGpWcmJWVTQ5dzBSemtJRU9pcDZlSy1UenZvb3ozOW5oRQ&q=https%3A%2F%2Fpypi.org%2Fproject%2Faiohttp%2F&v=3ZwlzOlRBbA)

### Code

See Domo-Dojo Notebook for ipynb file.

### Authentication

import requests
import dotenv
import os

dotenv.load_dotenv('env.txt')
domo_username = os.environ.get('DOMO_USERNAME')
domo_instance = os.environ.get('DOMO_INSTANCE')
domo_password = os.environ.get('DOMO_PASSWORD')

print(domo_instance)
def get_full_auth(domo_instance, domo_username, domo_password) -> str:
url = f'https://{domo_instance}.[domo.com/api/content/v2/authentication](https://domo.com/api/content/v2/authentication)'

body = {
'method': 'password',
'emailAddress': domo_username,
'password': domo_password
}

res = requests.request(method='POST', url=url, json=body)
data = res.json()

return data.get('sessionToken')

session_token = get_full_auth(domo_instance, domo_username, domo_password)
print(session_token)

### Get cards on a Page

from pprint import pprint

def get_cards_on_page(session_token, domo_instance, page_id):

url = f"https://{domo_instance}.[domo.com/api/content/v3/stacks/{page_id}/cards](https://domo.com/api/content/v3/stacks/%7Bpage_id%7D/cards)"

# headers = {'x-domo-authentication': session_token }
headers= {'x-domo-authentication' : session_token }

res = requests.request(method='GET',
url=url,
headers=headers)
return res.json()

data = get_cards_on_page(session_token, domo_instance, page_id = -100000)
pprint(data)

# use list comprehension to print results
cards_list = data.get('cards')

# for card in cards_list:
#     print(card.get('id'))

cards_list = [card.get('id') for card in cards_list]
cards_list

### Define the test for if card is 'broken'

import datetime as dt
import time

def what_time_is_it():
now = [dt.datetime.now](https://dt.datetime.now)()
return now.strftime("%H:%M:%S")

def is_card_broken(domo_instance, session_token, card_id) -> dict:
start = what_time_is_it()

url = f"https://{domo_instance}.[domo.com/api/content/v1/cards/kpi/{card_id}/render?parts=dynamic,summary](https://domo.com/api/content/v1/cards/kpi/%7Bcard_id%7D/render?parts=dynamic,summary)"

headers= {'x-domo-authentication' : session_token }

## not all APIs respond in the same amount of time.  'synchronous' code runs in a sequence
res = requests.request(method='PUT',url=url, headers=headers , json = {})
data = res.json()

## to prove the point, pause execution for two seconds.
time.sleep(2)
end = what_time_is_it()

## always return the same result for success or failure
base_res = {
'start' : start,
'end': end,
'card_id' : card_id
}

if data.get('status') == 400:
return {'renders' : False,
'message' : data.get('details').get('error'),
** base_res}

return {
'renders' : True,
'message' : 'success',
** base_res
}

#Test Render Function
## works fine
print( is_card_broken(domo_instance, session_token, card_id = 101681077))

## intentionally broken
print( is_card_broken(domo_instance, session_token, card_id = 1459762977))
## Rewrite as an Async function

import asyncio
import aiohttp

async def is_card_broken(domo_instance, session_token, card_id, session):

start = what_time_is_it()

url = f"https://{domo_instance}.[domo.com/api/content/v1/cards/kpi/{card_id}/render?parts=dynamic,summary](https://domo.com/api/content/v1/cards/kpi/%7Bcard_id%7D/render?parts=dynamic,summary)"
headers= {'x-domo-authentication' : session_token }

# res = requests.request(method='PUT', url=url,headers=headers)
# data = res.json()
# time.sleep(2)

res =  await session.put(url=url, headers=headers, json = {})
data = await res.json()

await asyncio.sleep(2)

end = what_time_is_it()

base_res = {
'start' : start,
'end': end,
'card_id' : card_id
}

if data.get('status') == 400:
return {'renders' : False,
'message' : data.get('details').get('error'),
** base_res}

return { 'renders' : True, 'message' : 'success', ** base_res }

[session](//testsession) = aiohttp.ClientSession()

tasks = []
for card in cards_list:
tasks.append(     is_card_broken(domo_instance, session_token, card, session = session))

tested_cards = await asyncio.gather(*tasks)

await session.close()

for test in tested_cards:
print(test)
