---
title: "[Advanced Video Tutorial] Manage Credentials in Domo Jupyter Notebooks with Accounts Integration and Python DataClasses"
url: /c/developerdomocom-community-edition/manage-credentials-in-domo-jupyter-notebooks-with-accounts-integration-and-python-dataclasses
author: Jae Myong Wilson
published_date: Oct 21, 2022
updated_date: Nov 26, 2022 at 10:58 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# [Advanced Video Tutorial] Manage Credentials in Domo Jupyter Notebooks with Accounts Integration and Python DataClasses
**Author:** Jae Myong Wilson
**Published:** Oct 21, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Printing and storing credentials in plain text is a big faux pas in the developer world.  Domo has new functionality that allows us to access the Accounts Object within Jupyter Notebooks ([kb link](https://domohelp.domo.com/hc/en-us/articles/360047400753-Jupyter-Workspaces#11.0.5.)).

Once you've accessed the Accounts object, store the credentials in a python dataclass ([documentation](https://docs.python.org/3/library/dataclasses.html)).  This will allow you to control representation (what happens when you print) as well as create standard and class methods attached to the class.
﻿

﻿
Define the Credential Class

from dataclasses import dataclass, field

@dataclass
class Credential:
domo_username:str
domo_password:str = field(repr = False)
domo_instance:str

session_token : str = field(default = None, repr = False)

@classmethod
def from_abstract_account(cls, account_name):
import domojupyter as domo
import json

account_str = domo.get_account_property_value(account_name, 'credentials')
creds_obj = json.loads(account_str)

return cls(domo_username = creds_obj.get('DOMO_USERNAME'),
domo_instance = creds_obj.get('DOMO_INSTANCE'),
domo_password = creds_obj.get('DOMO_PASSWORD'))

def say_hi(self):
print(f"hello my name is {self.domo_username}")

def get_full_auth(self) -> str:
import requests

url = f'https://{self.domo_instance}.[domo.com/api/content/v2/authentication](https://domo.com/api/content/v2/authentication)'

body = {
'method': 'password',
'emailAddress': self.domo_username,
'password': self.domo_password
}

res = requests.request(method='POST', url=url, json=body)
data = res.json()

if data.get('sessionToken'):
self.session_token = data.get('sessionToken')

return self.session_token

Map over a list of the desired credentials

account_list =['Valid Creds', 'Fake Credentials', 'Fake Creds_v2', 'Fake Creds_v3']

cred_store = [ Credential.from_abstract_account(account_name) for account_name in account_list]
Get a Session Token for the first credential in the credential store.

print(cred_store[0])
cred_store[0].get_full_auth()

#ISolvedItWithDomo
#Domo
#DomoCommunity
#DomoSensei
