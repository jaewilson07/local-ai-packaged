---
title: "Breaking Up a String into Single Values in Magic ETL"
url: /c/developerdomocom-community-edition/breaking-up-a-string-into-single-values-in-magic-etl
author: Mark Snodgrass
published_date: Nov 30, 2022
updated_date: Nov 30, 2022 at 10:05 AM
tags: ['MajorDomo', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# Breaking Up a String into Single Values in Magic ETL
**Author:** Mark Snodgrass
**Published:** Nov 30, 2022
**Tags:** MajorDomo, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Creating a word cloud in Domo is a great way to visualize the most popular terms in a dataset. However, if your dataset contains sentences, or phrases, this becomes problematic. In this video, I will show you how to use Magic ETL to break up a string of words into individual words in order to create a meaningful word cloud.
﻿

﻿

In order to break something up into individual values, there needs to be an identifier that can be used to break up the string. In this case, it would be a space. Since every string can have a varying amount of words in it, I need to determine how many words are in the string. I can do this by using a couple different functions. I can use the LENGTH() function to see how many characters are in a string. I can then use the REPLACE() function to replace spaces with no space and use the LENGTH() function again to see how long the string is with no spaces. Subtracting the difference between the two will tell me how many spaces are in the string.

The next step is to join your data to a sequential list of integers. In my example, I used the Domo Calendar dataset and took the day of year column from a single year to give me a list of numbers that went from 1-365. To join the two datasets together, create a constant in each dataset and then join on that value. This will temporarily increase the size of the dataset as it will (in my case) create 365 rows for each row in your dataset.

Ater joining, you can filter your data to where the number in your integer dataset is less than or equal to the number of spaces that you calculated in your dataset. After filtering, each row in your dataset should only be repeated for the number of spaces that the string has.

You can now dynamically split your string by using the SPLIT_PART() function. You will split your word on your identifier (a space, in my example) and use the value from your integer dataset to select which part. You now have each word broken out as a single word as its own row.

As an optional final step, you can remove common words, such as: and, the, or, etc.. by joining to another dataset that contains your common words and then using the filter tile to filter out those rows. In this join, it is important that your words are in the same format, such as all uppercase, or lowercase. You can use the UPPER(), LOWER(), or INITCAP() functions to normalize both strings prior to joining to ensure they match properly.

This process can be used to break up other strings, such as comma separated values. I hope you found this helpful!
