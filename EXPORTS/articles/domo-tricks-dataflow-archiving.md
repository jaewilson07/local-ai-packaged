---
title: "Domo Tricks: Dataflow Archiving"
url: /c/developerdomocom-community-edition/domo-tricks-dataflow-archiving
author: Bryan Van Kampen
published_date: Oct 28, 2022
updated_date: Nov 26, 2022 at 10:58 AM
tags: ['Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# Domo Tricks: Dataflow Archiving
**Author:** Bryan Van Kampen
**Published:** Oct 28, 2022
**Tags:** Domo Sensei
**Categories:** Tutorials and Code Snippets

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeElGZWc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--60e2c512f60a4842ff0776ef02c17bfb0e8c85ca/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lKYW5CbFp3WTZCa1ZVT2hSeVpYTnBlbVZmZEc5ZmJHbHRhWFJiQjJrQ09BUXdPZ3B6WVhabGNuc0dPZ3B6ZEhKcGNGUT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--bbf79c16c44963bdeaaeb388703e95ba07b6ce59/Archive.jpeg)

---

Everyone's done it. You've built out some incredible dataflow that will revolutionize the way your organization operates and 100x the revenue. Fast forward a year, and you're somehow the only card viewer and have millions of rows hanging out in your [#Domo](https://www.linkedin.com/feed/hashtag/domo) instance not being used.

Data Governance and regular clean-ups are an important part of keeping your Domo instance user friendly and compliant. However, there's sometimes value in keeping the business/dataflow logic and not the extra unused data.

﻿
![](https://media-exp1.licdn.com/dms/image/D5612AQH6APApdDyWlg/article-inline_image-shrink_1500_2232/0/1665435701448?e=1672272000&v=beta&t=GTrG0XqKbFHDxLdsLTG0NZDKByTF1MY-FTimQXICfdY)
﻿

If you've labored over the dataflow and business logic but the dataset isn't being used and you're sick of the millions of unused rows, consider implementing a standard dataflow archiving process in your instance as part of your governance procedures:

- Rename the dataflow/datasets and add an "Archive" description, or whatever makes sense based on your organization's naming conventions (i.e., "Archive | Amazing 100x Revenue Idea"). I'd also add a description to the dataflow and dataset that explains that it has been configured to output zero rows.

- If your organization utilizes tags, add an [#Archive](https://www.linkedin.com/feed/hashtag/archive) tag.

- Remove any schedules so the dataflow stops running on a schedule or when the input datasets update.

- Configure the dataflow's outputs to return zero rows, which can easily be done in both MySQL and Magic dataflows:

**
MySQL
**

In the final output(s), add some nonsense logic that will never be true in your where clause. I'm impartial to "where 1 = 0:"

﻿
![](https://media-exp1.licdn.com/dms/image/D5612AQESqCYZJq8RBQ/article-inline_image-shrink_1500_2232/0/1665436320773?e=1672272000&v=beta&t=W8RO7XYNY-x6IlKdQxpZW9BHTdat8D8-znR7GA4eXKk)
﻿

**
Magic ETL
**

The core logic is the same in Magic ETL as it is in MySQL dataflows. In order to output zero rows in your Magic ETL datasets, add a filter tile right before your output dataset(s) and populate logic in your filter formula that will never equate to true:

﻿
![](https://media-exp1.licdn.com/dms/image/D5612AQGxxJbJydxL3g/article-inline_image-shrink_1500_2232/0/1665437257960?e=1672272000&v=beta&t=cP2tEab50F6sFNARZTiXE-UMty2V88TFp3JlMY54yks)
﻿

Run the dataflow one last time, and it will return datasets with zero rows. You still have the business and dataflow logic if the project gets revisited, but it's not taking up valuable rows in your Domo instance.

What are other [#DomoGovernance](https://www.linkedin.com/feed/hashtag/domogovernance) tips and tricks you have?
