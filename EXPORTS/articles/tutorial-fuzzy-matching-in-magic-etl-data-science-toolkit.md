---
title: "TUTORIAL -- Fuzzy Matching in Magic ETL // Data Science Toolkit"
url: /c/builders-club/fuzzy-matching
author: Jae Myong Wilson
published_date: May 18, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# TUTORIAL -- Fuzzy Matching in Magic ETL // Data Science Toolkit
**Author:** Jae Myong Wilson
**Published:** May 18, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBenNWREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--dc8222ade1a892d7b377b9c72c0a9c56acd31442/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/Luma%20(4).jpg)

---

I'm trying to build a fuzzy matching use case for a client.

Fuzzy Matching is the process where you try to match a string against a set of strings.

### Use Case overview

Imagine you have a list of cleaned and conformed customer addresses which you maintain in SalesForce, and you receive dirty data from an Uber pull and you want to match and see if your Uber customers exist in your Salesforce.

For each Uber address you'd compare it against all your Salesforce addresses and ask "which salesforce addresses are the closes match to what I got from Uber?

There's a handful of different scoring methods, but the general idea is, "how many letters do I have to change in the Uber data before it is equal to a value in my Salesforce data?"  The strings with the fewest number of changes will be 'the best match.'

[https://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/](https://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/)

# Import the domomagic package into the script
from domomagic import *
import pandas as pd

from fuzzywuzzy import process
from fuzzywuzzy import fuzz

# read data from inputs into a data frame
new_df = read_dataframe('New')
master_df = read_dataframe('Master')

# write your script here
score_sort = [(x,) + i
for x in new_df['new']
for i in process.extract(x, master_df['master'], limit = 1,   scorer=fuzz.token_sort_ratio) ]

print(score_sort)

#Create a dataframe from the tuples
write_dataframe(pd.DataFrame(score_sort, columns=['new','master','score_sort', 'orig_pos']))

### Next Steps

Develop a workflow that accepts user input.  I should mark the 'correct matches' and ideally store incorrect matches too.

Sample Implementation here
[https://domo-dojo.domo.com/datacenter/dataflows/37/graph](https://domo-dojo.domo.com/datacenter/dataflows/37/graph)

Output Dataset﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBME1WREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--5280eb9fcd11d8dbbbf798356202687f4b99d727/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
