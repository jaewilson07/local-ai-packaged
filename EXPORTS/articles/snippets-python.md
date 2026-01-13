---
title: "SNIPPETS - Python"
url: /c/developerdomocom-community-edition/simple-python-snippets
author: Jae Myong Wilson
published_date: Sep 22, 2021
updated_date: Oct 11, 2021 at 09:36 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# SNIPPETS - Python
**Author:** Jae Myong Wilson
**Published:** Sep 22, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

### Create a Dataset in Domo

original source: [https://dojo.domo.com/discussion/53359/importing-data-from-spyder-locally-to-domo#latest](https://dojo.domo.com/discussion/53359/importing-data-from-spyder-locally-to-domo#latest)

from pydomo import Domo

domo = Domo('client-id','secret id', api_host='[api.domo.com](https://api.domo.com)') (as mentioned in the link)

d = domo.ds_create(df, 'name you want to provide in DOMO')
