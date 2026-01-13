---
title: "Things I heard at Domopalooza 2023"
url: /c/articles-and-knowledge-base/things-i-heard-at-domopalooza-2023
author: Jae Myong Wilson
published_date: Apr 3, 2023
updated_date: Apr 03, 2023 at 06:12 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
likes: 1
---
# Things I heard at Domopalooza 2023
**Author:** Jae Myong Wilson
**Published:** Apr 3, 2023
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

---

Domo hinted at unveiling of a ton of new features at Domopalooza 23.  Here are some of my thoughts as well as resources I've coalesced during the event.﻿

[

](#remove-attachment)

[

![](https://www.domo.com/assets/images/og-image-1200x630.png)

New Product Features | Domo

Domo enables all employees to engage with real-time data, increasing alignment, collaboration and productivity across the entire organization.

https://www.domo.com/product/new-features

](https://www.domo.com/product/new-features#/)

﻿

Your CSM should have all the information, but sometimes you gotta ask around in the [Slack](https://domousergroup.carrd.co) group for the inside scoop.

Link to current [release ](https://domo-support.domo.com/s/article/Current-Release-Notes?language=en_US)notes

## [**New Chart Types**](https://www.domo.com/product/new-features#bi-analytics-new-chart-types)

**Sankey Chart **has been updated to handle flows containing a circular reference

- [https://domo-support.domo.com/s/article/360043429273?language=en_US](https://domo-support.domo.com/s/article/360043429273?language=en_US)

Pretty big unlock for people tracking customer journeys through web pages!

**Slope Chart **-- This simplified line chart allows users to easily visualize and calculate changes in each value or set of values across a time-period, helping to understand the magnitude of change.

- [https://domo-support.domo.com/s/article/000005154?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005154?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0STG8p7kg%24)

I have mixed feels about this, looks like all it's calculating is percent change ... which isn't a terrible thing, but I think typically you want to see all of the values and then calculate the slope.  Not a big add IMHO.

**Variance and Difference Chart **-- The Variance or Difference Chart compares two related series (such as budget vs. spend or sales forecast vs. actual sales) to understand the difference at various points in time.

- [https://domo-support.domo.com/s/article/000005156?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005156?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QNjZmbDA%24)

Man, if you just want to know how much you were over or under just subtract actuals from budget and graph it on a zero based axis!

[**Table Calculations**](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*bi-analytics-table-calculations__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QPTXpMmQ%24)** – **Table Calculations allows for quicker and easier
insights by removing the need to build DataFlows or Beast Modes to show
calculations like the ranking or percent of a column.

- [https://domo-support.domo.com/s/article/360043429573?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/360043429573?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0SMQest4A%24)

THIS IS HUGE.  SPEND A LOT OF TIME HERE.  I can't tell if the Window functions in the viz layer are calculated in the client (by the viz layer) or if the functions are sent as queries to the SQL database (a la window functions).  It ALMOST doesn't matter, except it would be good to know and understand so that you can predict outcomes.  I know that FIXED functions operate in a manner different from WINDOW functions ... so take your time.

[**New DOMO Bricks:**](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*app-creation-tools-new-domo-bricks-formerly-ddx-bricks__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0RkBYwQ0g%24)** **We have added a new batch of DOMO (formally DDX)
Bricks that emphasize our commitment to “an app for every action.” As always, these Bricks are easy to use and adaptable with little to no code.
Drag-and-drop them right into your Stories from the Appstore to get powered up as quickly as possible.

**4 Charts in 1**

**SugarForce**

**Beast Mode Support**

**Table All Columns **

**Organizational Chart**

**To-Do List**

**Gantt Chart**

**Calendar**

- [https://domo-support.domo.com/s/article/4423762260375?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/4423762260375?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0RN86KKkQ%24)

OK, I was pretty vocal about how much I did not care for DDX bricks when they launched.  Since then I've seen a ton of people adopt baby DDX projects, so on one hand, I guess that's enablement.  I would argue that all of the boiler plate could just be moved to a custom app ... and you'd have linting from VS Code.

[**MS Office Add-in Enhancements**:](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*bi-analytics-enhancements-to-microsoft-office-add-ins__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QPpKzGlQ%24) The new MS Office Add-ins bring the unmatched Domo user experience to your favorite MS Office applications. The Microsoft Office Add-ins allow for a direct two-way connection between Domo and Microsoft Word, Excel, PowerPoint, and Outlook.
These enhancements allow users to get work done faster and smarter by improving the ability to bring the data directly to where productivity happens.

**Import Data Previews**

**Page Filter Support**

**Include Card Titles and Summary Numbers on Import**

**Configure Column Data Type**

**Drag and Drop Cards into Office Documents**

**Content Control in MS Word**

**Search Functionality for Page Filters**

**Hover Preview for Uploads**

**Batch Data & Time**

**Display Filter Settings**

**Highlighted Data Creation (Excel only)**

**Content
Refresh (Powerpoint)**

- Microsoft 365 Installation guide: [https://domo-support.domo.com/s/article/000005146?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005146?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0TyRQMhrw%24)

- Microsoft 365 Desktop app: [https://domo-support.domo.com/s/article/000005143?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005143?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0SIJGQzSA%24)

- Microsoft 365 Enterprise Installation guide: [https://domo-support.domo.com/s/article/000005145?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005145?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0TORYqhWw%24)

[**Custom and List Attributes for Groups:**](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*data-foundation-custom-attributes-in-groups__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0TgQFpQzA%24)** **Admins can now create custom attributes that align with their SSO directories. These attributes can be multi-valued and can be used to define membership of dynamic groups. These can be automatically imported through the Identity Provider or managed directly within Domo.

- [https://domo-support.domo.com/s/article/000005164?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005164?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0SuilkvlA%24)

I haven't done a ton of focus on security config in Domo, but being able to have your own trusted attributes instead of just the out of the box attributes seems pretty big especially if you're digging into dynamic groups or dynamic PDP.

PRO TIP re Dynamic PDP.  At the moment, Domo does not support using dynamic attributes on Users to create dynamic PDP policies.  So instead, use dynamic attributes to create dynamic groups, and then assign those groups to PDP policies.

Also, I would argue you should never create policies for individuals anyway so while that sounds like a limitation, I think that's fine.

[**Partition/Subset Processing in Magic **](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*data-foundation-subset-processing-in-magic-etl__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QfqoLDKA%24)**ETL: **With this feature, Magic ETL now supports processing subsets of data by loading and running data incrementally, rather than having to perform full replace operations at each execution. This new capability can provide greater data integrity and reduce processing load to make your DataFlows more resilient and flexible than ever!

- [https://domo-support.domo.com/s/article/000005150?language=en_US](https://urldefense.com/v3/__https:/domo-support.domo.com/s/article/000005150?language=en_US__;!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0TCljMKyA%24)

BIG NEWS!  Take the time to understand Partitioning.  I don't feel Subset processing adds anything radically huge unless you are performing targeted updates of datasets.
Subset processing makes sense if you're APPENDing your input datasets, but the value add of Partitioning is that it introduces flexibility to your data pipeline by supporting deduplication.  IMHO if your goal is deduplication, your inputs should be REPLACE, making subset processing superfluous.

[**Domo Everywhere Additions:**](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*data-distribution-domo-everywhere-enhancements__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QLJOEpEw%24)

**Default Sharing Rules **– Subscribers can be allowed to configure default access rules for content based on publisher domain.

**Auto Subscribe **– Allows for automation of tasks required during the content subscription process, making this step easier than ever!

**Programmatic DataSet Switching**—This feature allows users to choose which DataSet is powering any card or dashboard in an embedded context. This allows for our users to create smart embedded solutions that show user-specific views of data.

**Publish: Summary Table Sorting and Filtering – **Publication jobs can now be sorted and filtered for easier review.

**Support for Domo Bricks – **All the power and possibilities of Domo Bricks are now available for publications! Domo Everywhere users now have an additional tool to enhance their publish analytics solutions.

I don't use publish much, and when I do I'm usually scripting workflows around accepting subscriptions, configuring content sharing and handling PDP, but I love the attention Domo is putting into Publish.  Domo  Everywhere is IMHO a unique selling point amongst BI and big data "data experience" platforms, so I'm happy to see development in this space.

[**Cloud Amplifier Improvements (Formally Multi-Cloud):**](https://urldefense.com/v3/__https:/www.domo.com/product/new-features*data-foundation-domo-cloud-amplifier__;Iw!!JmoZiZGBv3RvKRSx!7izYFLQUx_wftCnklKXbW85Z1kbVSuHPiPn6mW9GoJSNztYjmgHyiVkqyubufOw9gQ3ffmqbbLy8eUmeBe44v0QVhjuPgg%24) Domo Cloud Amplifier allows for incredible flexibility to integrate Domo with existing enterprise cloud infrastructures. This tool gives users the power to build custom, high-performance, bi-directional pipelines catered to any business need. The following improvements will be available for Cloud Amplifier:

**Domo Workbench Support **

**Snowflake (Read and Write) **

**Dremio (Read) **

**BigQuery (Read)**

**DataBricks (Read) (BETA) **

**RedShift (Read) (BETA)

**Oh man, I wish Domo would pick a name for a product and not just rename it every other year.  But OK.  I'm intrigued to see how much traction this offering gets.  it is on paper very cool, but I suspect given the way Domo was originally built, a lot of consideration was not put in place on how to create tooling for monitoring and administering usage in a consumption model.

Remember, back in the day Domo was sold on a per user license basis and everything was all-you-can-eat.

- As Domo started releasing "premium features" (probably to recoup the cost of development),

- or Domo product became so good, users could do increasingly wasteful things, (like run dataflows every 15 minutes even if the underlying data hadn't changed) or execute connectors which then triggered dataflows with no new data)

- The Partition BETA has to go on hold because the product was great, but users didn't understand how to use them effectively!  Guardrails were thrown in place to prevent users from using Partitions as UPSERT (one row per partition! AUGH)

As Domo usage became increasingly less profitable, consumption was adopted, but from the ground up, Domo was designed without consideration for consumption.  As we stack Domo on top of platforms that ARE consumption focused, I expect there to be a lot of backlash as users wrack up massive Snowflake bills ... but let's see!
