---
title: "Naming conventions and easier reference"
url: /c/builders-club/naming-conventions-and-easier-reference
author: Michael Sattler
published_date: Nov 2, 2021
updated_date: Nov 26, 2022 at 10:56 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
comments: 1
---
# Naming conventions and easier reference
**Author:** Michael Sattler
**Published:** Nov 2, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

---

Here's an issue I could use some suggestions on: as our datasets and dataflows multiply (deployed our data lake in March and it has mushroomed quickly), we're having a hard time keeping them straight. We have a team of 2-3 creating and using them so we've tried to standardize so it doesn't all flow through one person's head. What have people found the best way to name things?

We've been trying something like this for datasets
[data source]_[relevant table/s]_BASE

But 80% of our data comes from one source (with a long name) and when the set has joined data that middle bit gets unwieldy. Plus the Domo menus routinely truncate the useful stuff off the end so it's hard to select the right one as you're going along. What do y'all do? Do people really write long descriptions as they build datasets/dataflows and expect them to be read?

Oh and do people advise all_lower, Title Case, or camelCase for naming?
