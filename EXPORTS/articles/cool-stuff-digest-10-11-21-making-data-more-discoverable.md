---
title: "Cool Stuff Digest 10/11/21 - Making Data More Discoverable"
url: /c/articles-and-knowledge-base/cool-stuff-digest-10-11-21-making-data-more-discoverable
author: Jae Myong Wilson
published_date: Oct 11, 2021
updated_date: Nov 26, 2022 at 10:54 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# Cool Stuff Digest 10/11/21 - Making Data More Discoverable
**Author:** Jae Myong Wilson
**Published:** Oct 11, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBOVFuR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d85a969443275fd23fe4f22fd2fe1eebb41bc4b6/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/Luma%20(2).jpg)

---

Links to [slides](https://www.slideshare.net/TamikaTannis/neo4j-graphtour-santa-monica-2019-amundsen-presentation-173073727) from Video
﻿

﻿
This week I've been thinking about Data Discovery.  It was interesting to catch some ideas from technologists and enthusiasts using other platforms, and try to align that with "what does Domo do well?" or "what kind of automations or tools can we use to do Domo better?"

## Organize MetaData into Schemas

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMUluR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--8f90965d7e24985ab3265363f18eb05ec80ba0b2/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿

An idea I liked was this idea of organizing metadata into a schema (a structured table) potentially based on tags.  So I did a loooonnnngggg tutorial about that.

The idea being, you schema could include concepts (what was the data about?  a customer, projects expenses, item sales, opportunities or leads?)  And this would be separate from the data source.  Customer data could come from Hubspot, SalesForce, Dynamics or Shopify.

We know we'd ultimately combine all this raw data into a dashboard dataset in ETL, but for the Data Scientist or Data Governance team, wouldn't it be grand if the data center was a little more searchable without crawling through the lineage diagram?

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBM01uR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--bfed74272d314cb1ed63f4edb11b8183b79e5fd2/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
﻿

﻿

## Using Networks to discover data

Another interesting idea I came across was the idea of conducting a network analysis to see which datasets are interesting.  I.e. "You're related to this person (in a social network) therefore you might be interested in this dataset."

[https://engineering.atspotify.com/2020/02/27/how-we-improved-data-discovery-for-data-scientists-at-spotify/](https://engineering.atspotify.com/2020/02/27/how-we-improved-data-discovery-for-data-scientists-at-spotify/)

﻿

﻿
Domo does have that built into the product, but it's not reportable.  An interesting challenge might be to try to automate maintaining the employee chart API and intersect that with the activity log API to see which cards or datasets your boss uses and then report that in a card.

I think the truly fascinating question is to say "how do you know if a dataset is valuable?" and then convert that into a solution!

### Stuff you'd want to Automate

Grant S talked about a process for deleting or archiving aging content by using a weighted average scoring method.

﻿

﻿
Other Metrics of interest might include adherence to naming conventions, the presence of descriptions or tags, certification, and frequency with which columns are used.

On the Analyzer side, the big one was finding a way to identify duplicated or overlapping beast modes.

## Google is Copying Domo.

Or maybe Domo is copying Google.  Either way it was interesting to see the overlaps in their technology/offering.
﻿

﻿
