---
title: "TUTORIAL: Automatically secure and tag your datasets // PDP, Impact Analysis, Tagging, JavaScript &amp; Domo"
url: /c/builders-club/tutorial-secure-all-your-datasets-containing-sensitive-data-impact-analysis-javascript-domo
author: Jae Myong Wilson
published_date: Sep 28, 2021
updated_date: Jun 20, 2022 at 05:46 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# TUTORIAL: Automatically secure and tag your datasets // PDP, Impact Analysis, Tagging, JavaScript &amp; Domo
**Author:** Jae Myong Wilson
**Published:** Sep 28, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNFdZRnc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--40b04a2e93d7199bf66edea89d54b2568ed6a3ab/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Luma%20(13).png)

---

## Why you need this tutorial:

### PDP is the only way to secure your data

When you upload data into Domo, the only way to guarantee that people don't accidentally see the wrong data is by enabling PDP.
[https://domohelp.domo.com/hc/en-us/sections/360007334593-Personalized-Data-Permissions-PDP-](https://domohelp.domo.com/hc/en-us/sections/360007334593-Personalized-Data-Permissions-PDP-)

> Even if you have PDP enabled on a dataset, if you build new datasets off of it (via ETLs) the new outputs DO NOT inherit PDP policies (dataset views do inherit PDP policies).

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBOHJQR0E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d9e268cedba26a4369d06d9c0061e64ea99b271f/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿

### Tagging helps users categorize and search the datacenter quikly.

Data Discovery and Self-Service BI are the dream.  Tagging is a great tool for making that a reality because users can rapidly search for datasets, set up certification and reporting pipelines based on tagged content as well as enrich the metdata around their datasets.

Tagging datasets manually gets stale quickly so automation based on the lineage API is a great way to offload that manual process.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBOWpQR0E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--72aee6b996e9966f99b19639c716ed6f3edd4994/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿

## Core Tools Needed

- Full Authentication workflow (we are using public but undocumented APIs)

- Query Data Lineage

- Data Policies API

- Dataset/Tags API

## Dynamically Enable PDP based on an impact analysis

##
﻿

﻿

For a DATASET_ID, perform an impact analysis, a lineage query where *traverseUp* is false.

export const ds_get_lineage = async (
DATASET_ID,
DOMO_INSTANCE,
sessionToken,
isTraverseUp = true
) =>
await get_data(
`[https://${DOMO_INSTANCE}.domo.com/api/data/v1/lineage/DATA_SOURCE/${DATASET_ID}?traverseUp=${isTraverseUp}&requestEntities=DATAFLOW,DATA_SOURCE`](https://${DOMO_INSTANCE}.domo.com/api/data/v1/lineage/DATA_SOURCE/${DATASET_ID}?traverseUp=${isTraverseUp}&requestEntities=DATAFLOW,DATA_SOURCE`),
'GET',
sessionToken
);

Then for each dataset, enable PDP, in the body, send *enabled *is true

export const ds_enable_pdp = async (
dataset_id,
DOMO_INSTANCE,
sessionToken,
isEnable
) => ({
...(await get_data(
`[https://${DOMO_INSTANCE}.domo.com/api/query/v1/data-control/${dataset_id}`](https://${DOMO_INSTANCE}.domo.com/api/query/v1/data-control/${dataset_id}`),
'PUT',
sessionToken,
{
enabled: isEnable,
}
)),
dataset_id,
});

## Automate Tagging based on an impact analysis

﻿

﻿
To update tags, the biggest gotcha is that the Tags API expects you to send a list of ALL the tags applicable to the dataset (not just the one you want to add or remove).

We end up having to get dataset details and then do some sophisticated JavaScript coding to send an array of non-duplicated tags of interest.

## Full Authentication against undocumented APIs

To query the public API's you'll need to include a sessionToken as described here.

[https://datacrew.circle.so/c/developerdomocom-community-edition/full-authentication-with-domo-apis](https://datacrew.circle.so/c/developerdomocom-community-edition/full-authentication-with-domo-apis)

Walkthrough of the *auth* function and dotenv
﻿

﻿
Good luck!
