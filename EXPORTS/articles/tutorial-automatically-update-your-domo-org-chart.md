---
title: "TUTORIAL - Automatically Update your Domo Org Chart"
url: /c/builders-club/tutorial-automatically-update-your-domo-org-chart
author: Jae Myong Wilson
published_date: Oct 12, 2021
updated_date: Jun 20, 2022 at 05:46 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# TUTORIAL - Automatically Update your Domo Org Chart
**Author:** Jae Myong Wilson
**Published:** Oct 12, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeEZSR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--cfbb2be93ac457351effb59af07e436d0616bf48/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/YT_ST_DataScience%20(2).png)

---

Despite it's usefulness, syncing the org chart in Domo can be a pain if you have many employees or experience a lot of turnover.  Fortunately you can leverage the APIs to keep your og chart sync'ed with an HR system.

[Domo KB](https://domohelp.domo.com/hc/en-us/articles/360043439453-Viewing-and-Entering-Peers-in-Your-Company-Org-Chart)

For this tutorial, we're using a randomly [generated dataset](https://domo-dojo.domo.com/datasources/d9257748-c181-496e-8f9a-016ee99b4a14/details/data/table) based on the Domo Stats people dataset; however you theoretically would grab this data out your HR system.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMFJQR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--ae7499b7a5aa248ae73f673849a928a4dd281d9c/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
Note if you don't have access to [domo-dojo.domo.com](https://domo-dojo.domo.com), let me know, ﻿
[
Jae Myong Wilson
](https://datacrew.circle.so/u/d8050f8c?show_back_link=true)

﻿, and I'll sort you out.

On to the tutorial.  (P.S. if you haven't already, make sure to [subscribe](https://www.youtube.com/c/OnyxReporting_2/sub_confirmation=1).)

﻿

﻿

## Hitting the APIs is the easy part.

We just monitor network traffic for the correct shape of the request body.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMjlQR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--99ee11e09927fa48ed28cf7afc4d369faa891615/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
In our code we are creating an action for *reportsTo *but you could extend that code to include an action for *directReports*

export const users = async (DOMO_INSTANCE, config) => {
const { userId, body_arr, sessionToken, action } = config;
const DOMO_URL = `[https://${DOMO_INSTANCE}.domo.com/api/content/v2/users/${userId}`](https://${DOMO_INSTANCE}.domo.com/api/content/v2/users/${userId}`);

const body = {
reportsTo: body_[arr.map](https://arr.map)((el) => ({
userId: el,
})),
};

return await get_data(`${DOMO_URL}/teams`, 'POST', {
token: sessionToken,
type: 'full',
body,
});
};

We've covered authentication pipelines and the get_data function in [other tutorials. ](https://www.youtube.com/watch?v=JWacOyKbbz0)

## Getting and Structuring the Data is the Hard Part

We built the ds_dataset function on other tutorials, again we aren't going to use those bits, so I've removed those actions.

export const ds_dataset = async (developerToken, config) => {
const { action, schema, data, dataset_id, query } = config;

const URL = '[https://api.domo.com/v1/datasets](https://api.domo.com/v1/datasets)';

const data_resp = await get_data(
`${URL}/query/execute/${dataset_id}`,
'POST',
{
token: developerToken,
type: 'developer',
body: { sql: query },
}
);

return data_[resp.rows.map](https://resp.rows.map)((row_arr) =>
data_resp.columns.reduce((accum, col, index) => {
const s = {};
s[col] = row_arr[index];
return { ...accum, ...s };
}, {})
);
};

We are hitting [developer.domo.com](https://developer.domo.com) APIs so we need the developerToken authentication pipeline.

The data arrives such that each row is represented as an array of values with the keys (column names) stored in a separate array.  We restructure that data using a reduce function where we combine the keys and values into a nicely formatted javascript object.

Unfortunately, our data is in the wrong shape.  In the array, each row represents one relationship (reportsTo) and instead, we need to reshape the data so that each object represents a user and all of their relationships.

// get hierarchy data from Domo
const resp_data = await ds_dataset(developerToken, {
action: 'queryData',
dataset_id: DATASET_ID,
query: 'SELECT * from table',
});

// collapse the data from one row per relationship to one row per user
const user_obj = resp_data.reduce((accum, row) => {
// if the user exists AND the actionType already exists, add in the new relationship
if (accum[row.userID] && accum[row.userID][row.Action]) {
accum[row.userID][row.Action] = [
...accum[row.userID][row.Action],
row.bodyID,
];
// if the user exists (and the action does not) add in a new actionType
} else if (accum[row.userID]) {
accum[row.userID][row.Action] = [row.bodyID];

// the user is net new
} else {
accum[row.userID] = {};
accum[row.userID][row.Action] = [row.bodyID];
}
return accum;
}, {});

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNEZRR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--f6cd3015df18e67c9a268290d875c8d27bd8c6ab/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
At this point, our array has been converted to an object (note the squiggly braces) and each property represents a user and all their relationships.

Although objects allow us to enforce uniqueness (can't have two properties / users with the same name), we cannot iterate over the properties of an object.  So we have to turn it BACK into an array again.

const obj_arr = Object.keys(user_obj).map((key) => ({
userId: key,
...user_obj[key],
}));

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNkpRR1E9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--0c4cd3d1aa504dc6b330783d1386c9b5a7a3e5eb/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿
Notice how we open with a square bracket indicating that we're dealing with an array, where each element represents a user, but arrays have no concept of uniqueness (two elements could contain the exact same content).  The upside though is now we can iterate over each element of our array and issue an API request.

const resp = await Promise.all(
obj_[arr.map](https://arr.map)(async (user) => {
if (user.reportsTo) {
const body_arr = user.reportsTo;

return await users(DOMO_INSTANCE, {
sessionToken,
userId: user.userId,
action: 'reportsTo',
body_arr,
});
}
})
);

Hope that was helpful.

[jae@onyxreporting.com](mailto:jae@onyxreporting.com)
