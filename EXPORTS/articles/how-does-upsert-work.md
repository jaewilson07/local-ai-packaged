---
title: "How does UPSERT work"
url: /c/articles-and-knowledge-base/how-does-upsert-work
author: Jae Myong Wilson
published_date: Dec 8, 2022
updated_date: Dec 08, 2022 at 08:37 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# How does UPSERT work
**Author:** Jae Myong Wilson
**Published:** Dec 8, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

---

Courtesy of Gordon P in the Dojo Community

"Each upload (Dataset execution) is stored individually.
Each time you upload, Domo adds the data to the already indexed (Processed) data and determines 1: does that row already exist (based on the primary key) or is it a new row.If it exists, it overwrites the previous value from a previous upload.  if it doesn’t it adds a new row.If you need to change your schema, or remove any data, it would do a full re-index, where it starts back at your first upload, and indexes them 1 by one until it has rebuilt and determined the rows that should/should not exist in the dataset.TLDR: Domo keeps a historical record of rows updated on each execution and compares each upload with what it has established as current data to determine if a row should be replaced or a new row added"

[https://domousergroup.slack.com/archives/C013AKYGP5W/p1670490550141159](https://domousergroup.slack.com/archives/C013AKYGP5W/p1670490550141159)
