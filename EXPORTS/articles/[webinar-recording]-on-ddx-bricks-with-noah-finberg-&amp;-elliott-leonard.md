---
title: "[Webinar Recording] - On DDX Bricks with Noah Finberg &amp; Elliott Leonard"
url: /c/articles-and-knowledge-base/on-ddx-bricks
author: Jae Myong Wilson
published_date: Nov 2, 2022
updated_date: Nov 03, 2022 at 04:44 PM
tags: ['Freelancer', '+1', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
likes: 3
comments: 3
---
# [Webinar Recording] - On DDX Bricks with Noah Finberg &amp; Elliott Leonard
**Author:** Jae Myong Wilson
**Published:** Nov 2, 2022
**Tags:** Freelancer, +1, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNGRNZlE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--341d65c6e345e227b7f2103b1b58a83a537c934c/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Luma%20(1).png)

---

🎉Thank you to everyone who attended.  This webinar was hosted on 11/2/2022 by the DataCrew team in an effort to bring more DDX Bricks awareness to the Domo Community.

Special thanks to ﻿
[
Elliott Leonard
](https://datacrew.circle.so/u/3bc332af?show_back_link=true)

﻿ and ﻿
[
Noah Finberg
](https://datacrew.circle.so/u/06c29055?show_back_link=true)

﻿ for their participation!  🎉

Original Event Link - [https://datacrew.circle.so/c/events-170e7d/ddx-bricks-ama](https://datacrew.circle.so/c/events-170e7d/ddx-bricks-ama)

﻿

﻿

# Important Links

- [DDX Bricks KB ](https://developer.domo.com/docs/ddx-bricks/ddx-bricks-overview)

- 🧵 Join the Domo User Group [Slack](https://domousergroup.carrd.co/)[ ](http://domousergroup.com/coc)Community

- How to Access the Domo-dojo instance ([Dojo link](https://dojo.domo.com/main/discussion/55204/access-to-domo-dojo-instance))

- Community DDX Dashboard ([domo-dojo link](https://domo-dojo.domo.com/page/1614788699))

- 🎥 Elliott’s [YouTube Channel](https://www.youtube.com/channel/UCZfU64hdkKvuOxtWLO0FxnQ)

- 🎥 DataCrew [YouTube Channel](https://www.youtube.com/channel/UCpnWmFCBWyqBMJlw6ZxNokQ)

# Q&A and Resources

## Reading Datasets into DDX Bricks

🎥 [Webinar Link Demo 2](https://www.youtube.com/watch?v=15nXTopnRcI&t=704s)

### Use *Domo.get* to retrieve data from the APIs

[https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.get](https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.get)

This method works, but the SQL API might be easier to interpret/use

💎PRO TIP.  Take the time to learn and understand “Promises”

﻿
![](https://lh6.googleusercontent.com/4bOPmAieeiwjqReYcDYULD5Oo9H48eNFiUT205RkkMzgHWC0j0mx5Wwki7U3_Znnj6xwfwAoownruA9v1SUzPtkLNQ4HD9tIkw6beecu9NuYJAZ9Hf5-dhEHhWzLtoxuqvVlgfwBHkP7ujArkfK_zNOnQDGit4whCiGHT1Mex4u26n7qkx72S6z7QPzE)
﻿

This snippet says “wait till you get a response from your 4 APIs THEN … do something.

Imagine you have a brick that consumes data extracted from 4 APIs.  When you send your *domo.get()* request, you don’t know how long it’ll take your API to return a result.

Each .get() method returns a promise that eventually you’ll get something back, but instead of blocking code execution (synchronous execution), JavaScript allows us to move to the next line of code and come back to the promise when it has a result (asynchronous code execution).

💎  Where have you seen asynchronous code execution?

Have you ever visited a graphics heavy website with slow internet connection and seen a spinning loading icon while parts of the page finished loading?  Classic example of asynchronous code execution!

Alternatively, have you ever scrolled facebook and all the text loaded faster than the images?  Another example of a page requiring two different APIs AND asynchronous code execution.

[https://www.w3schools.com/js/js_promise.asp](https://www.w3schools.com/js/js_promise.asp)

### 💎The SQL API is even easier than *Domo.get*

** **[https://developer.domo.com/docs/dataset-api-reference/dataset#Query%20a%20DataSet](https://developer.domo.com/docs/dataset-api-reference/dataset#Query%20a%20DataSet)

When it comes to code you can execute in DDX bricks, it looks like you can only hit “public APIs” i.e. APIs documented under [www.developer.domo.com](http://www.developer.domo.com)

On Private Vs. Public APIs

- Get Outa the Domo UI - Domo IDEAS Exchange Conference Video [YouTube video](https://www.youtube.com/watch?v=hRwrZABP8RE)

**Are there limitations in the SQL API with queries?**

Balance what you execute as a query in the app vs. what you implement in ETL or a Dataset View.  The simpler the query, the faster the query response, and the snappier the app.

Theoretically, the SQL API is passing the same queries to the same database engine that resolves Dataset Views, so yes, theoretically subqueries should be supported in the SQL API… should you do it? … different question.

**How to have more than one dataset in DDX bricks?**

Use the DDX 10 Datasets Brick ([domo-dojo link](https://domo-dojo.domo.com/domoapp/card/edit/1786828858?page=1614788699&details=true))

### Pulling Parameters from the Environment

🎥 [Webinar Link Demo 1](https://www.youtube.com/watch?v=15nXTopnRcI&t=605s)

[https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.env](https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.env)

### Use a DDX Brick to apply a Page Filter

🎥 [Webinar Link Demo 5](https://www.youtube.com/watch?v=15nXTopnRcI&t=1347s)

[https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.filterContainer](https://developer.domo.com/docs/dev-studio-guides/domo-js#domo.filterContainer)

### Making your App react with Event Listeners and OnClick events

🎥 [Webinar Link - Demo 6](https://www.youtube.com/watch?v=15nXTopnRcI&t=1425s)

[https://www.freecodecamp.org/news/html-button-onclick-javascript-click-event-tutorial/](https://www.freecodecamp.org/news/html-button-onclick-javascript-click-event-tutorial/)

[https://www.w3schools.com/howto/howto_js_trigger_button_enter.asp](https://www.w3schools.com/howto/howto_js_trigger_button_enter.asp)

### Using Phoenix Library

🎥 [Webinar Link - Demo 4](https://www.youtube.com/watch?v=15nXTopnRcI&t=1138s)

[https://github.com/DomoApps/domo-phoenix](https://github.com/DomoApps/domo-phoenix)

[https://domoapps.github.io/domo-phoenix/#/domo-phoenix/properties](https://domoapps.github.io/domo-phoenix/#/domo-phoenix/properties)

The Phoenix library was implemented to provide a JavaScript charting library that looked and felt like Analyzer.

### Getting Started with State Management + AppDB

🎥 [Webinar Link - Demo 6](https://www.youtube.com/watch?v=15nXTopnRcI&t=1425s)

[https://developer.domo.com/docs/dev-studio-references/appdb](https://developer.domo.com/docs/dev-studio-references/appdb)

AppDb can be used to store form data or user interactions (aka “state management”)

💎 Where have you seen state management?

Any time you log into an app and it ‘remembers’ who you are or what was in your shopping cart.

[https://dev.to/abdurrkhalid333/what-is-state-management-and-why-you-should-learn-it-3kai](https://dev.to/abdurrkhalid333/what-is-state-management-and-why-you-should-learn-it-3kai)

## Additional Infrastructure and Development Skill

🎥 [Webinar Link - Noah's Intro](https://www.youtube.com/watch?v=15nXTopnRcI&t=418s)

🎥 [Webinar Link - the Value of an "App Platform"](https://www.youtube.com/watch?v=15nXTopnRcI&t=1875s)

What do they mean, by “Domo makes it easier to build and deploy an app?”

[https://developer.domo.com/docs/dev-studio/dev-studio-overview](https://developer.domo.com/docs/dev-studio/dev-studio-overview)

## 💎Development Pro Practices

### Use CodePen as a faster IDE (development environment)

🎥 [Webinar Link - Tip 3 - use CodePen](https://www.youtube.com/watch?v=15nXTopnRcI&t=2339s)

[www.codepen.io](http://www.codepen.io)

CodePen has great (simple) code samples built by the larger javascript community.  Integrate the examples into your DDX Bricks.

To mimic the *handleResults*() function in CodePen (which is NOT hooked up to the Domo API): *console_log(data)* and then copy/paste the results into your CodePen Javascript file as a new variable, *data*.  This allows you to develop code in CodePen after the point data was retrieved dynamically from the Domo’s Dataset API.

### Inspect your Browser to see how your HTML document is shaped.

🎥 [Webinar Link - Demo 1](https://www.youtube.com/watch?v=15nXTopnRcI&t=605s)

🎥 [Webinar Link - Tip 4 - using the Browser to inspect the DOM (rendered HTML document)](https://www.youtube.com/watch?v=15nXTopnRcI&t=2438s)

This can help you troubleshoot and debug how your app displays data in the browser.

Pro Tip.  Take the time to learn about DOM manipulation. (i.e. “Dynamically adding content to your webpage”)

[https://fundamentals.generalassemb.ly/11_unit/dom-cheatsheet.html](https://fundamentals.generalassemb.ly/11_unit/dom-cheatsheet.html)

If you want your app to be pretty, but spend less time “reinventing the wheel” learn about Bootstrap ([https://getbootstrap.com/](https://getbootstrap.com/))

If you’ve heard of React ([https://reactjs.org/](https://reactjs.org/)) this library is designed to simplify DOM manipulation.

If you’re competent in React, consider learning about MUI (previously MaterialUI, [https://mui.com/](https://mui.com/) )

### Consider using Save As Copy for Version Control

DDX Bricks don’t really integrate with any of Domo’s built in Version Control (or at least not in a way we can quickly access.

If you are making major revisions to your App, consider Saving your app as a copy.  Just like you can save your cards and change the columns, or filters, you can save a copy of your card and modify the code.

Alternatively, as you start building more sophisticated projects, consider saving your documents in folders backed up using GitHub.

## Other Questions

**If the DDX brick is published to another instance, will it know to use the respective dataset within that subscriber not the publisher?**

Apps can be deployed with sample datasets (like all the apps you’re deploying) there is no built-in wiring that integrates with publish.  That’s relatively niche.  You could write a script that handles wiring up the datasets (like the Quickstarts do).  Keep in mind that an app deployed to a different instance will ultimately consume a dataset with a different dataset_id so it’s hard to “just know” what the correct dataset is.

**is it always necessary to have a dataset even if it's not used?**

Each DDX Brick that YOU build is based on a baseline template (the app in the AppStore).  Those Templates have a fixed number of datasets available (in the blank app it has 3, in the 10 Dataset brick its 10)  Do you HAVE to use them? No.  But is there a max you can / could use?  Yes, as defined by the template.

**For Maps: Is it possible to go as granular a map based on postal codes for Germany?**

Are you talking about the standard apps in Analyzer?  It depends on what THAT chart type is capable of.

If you’re talking about a custom app built using SVGs that’s a different tool.  If you used a custom map, could you use a map that was divided by German postal codes?  Sure, if you can find that SVG.

[https://www.youtube.com/watch?v=eKOLhsfl10Q](https://www.youtube.com/watch?v=eKOLhsfl10Q)

If you want to use ArcGIS ([https://developers.arcgis.com/javascript/latest/](https://developers.arcgis.com/javascript/latest/)) or any other library, the answer is defined by the library you choose.

# Other Bricks of Interest

Filtering on multiple Columns (Ben Schein)

[https://www.domo.com/appstore/app/ddx-searchable-filter-app-multiple-columns/overview](https://www.domo.com/appstore/app/ddx-searchable-filter-app-multiple-columns/overview)

Example of Where used (this was initially a custom app and the code was migrated to a flexible DDX Brick for you! YAYYYY)

[https://www.domo.com/covid19/data-explorer/all/](https://www.domo.com/covid19/data-explorer/all/)
