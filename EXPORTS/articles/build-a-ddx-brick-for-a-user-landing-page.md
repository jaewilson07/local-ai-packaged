---
title: "Build a DDX Brick for a User Landing Page"
url: https://datacrew.circle.so/c/articles-and-knowledge-base/build-a-ddx-brick-for-a-user-landing-page
author: Jae Myong Wilson
author_tags: ['Admin', 'Freelancer', 'Domo Sensei']
space: Articles &amp; Knowledge Base
published_date: May 18, 2023
updated: May 18, 2023 at 06:33 PM
likes: 0
comments: 0
---

# Build a DDX Brick for a User Landing Page

**Author:** Jae Myong Wilson
**Credentials:** DataCrew Community Admin // Data Whisperer
**Tags:** Admin, Freelancer, Domo Sensei
**Space:** Articles &amp; Knowledge Base
**Published:** May 18, 2023
**Likes:** 0 | **Comments:** 0

---

Here's a project I worked on for a customer to build a DDX Brick that acts as a Landing Page that only shows pages the user has access to.

Special thanks to Jace M from [@DomoHQ](https://www.youtube.com/channel/UCLhtrgF6h4PP44nVRfSIovA)  for sharing this template with me and [@noahfinberg7364](https://www.youtube.com/channel/UCO77oy5CBBoaLOW1EWRMrJQ)  for all his help teaching me DDX things!

**DDX GitHub Repo** -- code lives here!**
**[https://github.com/jaewilson07/datacr...](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqa1AzeExUWmVaRlVKMmJYWGsySmx0MmN2enJwUXxBQ3Jtc0trZ2JwT2Znd3I3dWFrZTlXSzlOdDhoc2FBa09WTEdmakgxdXVybE1scE84WHdod2MwVGVyVElPUk8zYk5seEVodTdrNC1rTThYZkluZzUzdU1oZTNGbjBaeDgxc0ZyVnRSRjBzaGkwaUl3YS11ZjlJMA&q=https%3A%2F%2Fgithub.com%2Fjaewilson07%2Fdatacrew%2Ftree%2Fmain%2Fddx_bricks%2Fjaewilson07%2Fddx_page_navigation&v=cbpCxXoenKU)

**DomoLibrary Repo** -- python library I used to build the dataset powering the brick.
[https://github.com/jaewilson07/domo_l...](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqbkgteFhoR29KWWRuTWxJMk8xcnZfckNPTTZfd3xBQ3Jtc0tsZElMdk1KTnAyc2oyb05yMDZjVFpxaFZ5UE5vblVzdmRsVXphNzBFYzRpQkc2V0huaGlJeElxczJFMmtHdDJiZlRLa2dKTEd2VDdPZzlDUVV6T0R1bGhPb0JmQWI2a1J4bFNwQVU2WnAyel9BdFhfOA&q=https%3A%2F%2Fgithub.com%2Fjaewilson07%2Fdomo_library&v=cbpCxXoenKU)

**Support my work** - [https://venmo.com/jaemyong-wilson](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqbGZSMXBQY0VPb0JwV3VjcGpwOTB5R05GZ0xwZ3xBQ3Jtc0tta2paR2xFX1F5M1p4bkE3UzlIVWFwMXZOU1hJcUNfN0FfUU9sTE1CRW5yS1lJMjNZSWxvSUhmU3liUXh0enJacmNfdVVNaTRLbXBOeDREUm1zdjF5eUR5OWw2YmVqOGhyWG5CZnQ0c1VxNXdJOXpZaw&q=https%3A%2F%2Fvenmo.com%2Fjaemyong-wilson&v=cbpCxXoenKU)

**I'm sponsored by Argo Analytics**
If you need help with custom apps, talk to the guys over at [Argo Analytics](https://argoanalytics.ai/)

Join our 🧵 [Domo User Group Slack](https://domousergroup.carrd.co/%EF%BB%BF)
﻿




﻿

## A Quick Code Review.  

Although the code does flow top to bottom, notice that there are no clear boundaries to the code.  You can't really parameterize it easily, and the original code certainly can't recycle code blocks.  

In this original code snippet  domo.get() is an asynchronous function, whose result (data) will be passed directly into handleResult() which both shapes the data into a usable form (a list of dictionaries) and then paints the app.  

While it is nice to just have one long function, it's tough to troubleshoot or swap in new code.

var domo = window.domo;
var datasets = window.datasets;
var Query = window.Query;

// HTML Bootstrap Grid Configuration
var query = (new Query())
  .select('Logo', 'Text', 'URL', 'Order')
  .orderBy('Order', 'Ascending')
  .query(datasets[0]);

*domo.get(query, {format: 'array-of-arrays'}).then(handleResult);*

// Loop through result to build out grid
function handleResult(data) {
  // Restructure the array-of-arrays object into a usable object
  const rows = [data.rows.map](https://data.rows.map)(row => {
    return data.columns.reduce((acc, curr, index) => {
      acc[curr] = row[index];
      return acc;
    }, {});
  });

  // Loop through rows to create the grid objects
  let container = document.getElementById("grid");
  let counter = 1
  rows.forEach(row => (...paint my app ...))
Below, we've rewritten it a series of async functions where all the calls are in main().

Notice that get_data receives the dataset and Query class and then returns a processed dataset (the FOR LOOP has been integrated into get_data()).  

async function get_data(dataset, Query) {

  // HTML Bootstrap Grid Configuration
  const query = new Query()
    .select('Logo', 'Text', 'URL', 'Order')
    .orderBy('Order', 'Ascending')
    .query(dataset);

  data = await domo.get(query, { format: 'array-of-arrays' });

  return [data.rows.map](https://data.rows.map)((row) => {
    return data.columns.reduce((acc, curr, index) => {
      acc[curr] = row[index];
      return acc;
    }, {});
  });
}

async function main(window) {
  var domo = window.domo;

  data = await get_data( dataset = window.datasets[0], Query = window.Query);

  ... paint my app ...
}
I preferred a different endpoint for retrieving data, so I wrote get_data_v2, commented out the line in main() and added a new one.

async function get_data_v2(dataset, userEmail) {
  data = await [domo.post](https://domo.post)( `/sql/v1/${dataset}`,
    `SELECT * FROM ${dataset} WHERE lower(user_email) = '${userEmail}' and parent_page_title is null`,
    { contentType: 'text/plain' }
  );

  return [data.rows.map](https://data.rows.map)((row) => {
    return data.columns.reduce((acc, curr, index) => {
      acc[curr] = row[index];
      return acc;
    }, {});
  });
}

async function main(window) {
  var domo = window.domo;

  // data = await get_data( dataset = window.datasets[0], Query = window.Query);

  data = await get_data_v2(dataset = window.datasets[0], userEmail.toLowerCase());

  ... paint my app ...
}
Hope this helps!
