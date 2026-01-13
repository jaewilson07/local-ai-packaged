---
title: "My Attempt at a Custom Connector"
url: /c/builders-club/my-attempt-at-a-custom-connector
author: Elliott Leonard
published_date: Jan 7, 2022
updated_date: Jun 20, 2022 at 06:00 AM
tags: ['Master Hacker']
categories: ['Get Help']
likes: 2
---
# My Attempt at a Custom Connector
**Author:** Elliott Leonard
**Published:** Jan 7, 2022
**Tags:** Master Hacker
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBOE1aSkE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--aa876bddae14083aa05867523b8bda0acf4e2c4d/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Screen%20Shot%202022-01-07%20at%209.28.18%20AM.png)

---

I recently built a custom connector for a software called Gainsight (it's like the Salesforce of customer success). It was a much longer road than I anticipated, so I decided to share my top 5 learnings. Hopefully this will help you avoid some pitfalls when developing your own custom connectors!

-
**Watch the IDEA exchange session on this topic** ([https://www.youtube.com/watch?v=OQLwYgU9smc](https://www.youtube.com/watch?v=OQLwYgU9smc)). Lacey does an amazing job doing a high-level overview of how to use the custom connector IDE and drops nuggets of wisdom that could save you hours of development time.

-
**Developer.Domo.com is your best friend**. I would highly recommend bookmarking the reference page ([https://developer.domo.com/docs/custom-connectors/reference](https://developer.domo.com/docs/custom-connectors/reference)) as it outlines how to use the methods Domo provides. Since you are coding in Vanilla JavaScript, these are the only custom methods you'll be able to use.

-  **Third-party Connector Support is your 2nd best friend**. This team is awesome to work with, definitely email them ([connectorhelp@domo.com](mailto:connectorhelp@domo.com)) if you're running into issues. They'll also provide comments/feedback after you've submitted your connector for publishing. They were able to help optimize my data processing code, teach me how to process some complicated JSON payloads, and ensure user input was scrubbed to prevent malicious behavior.

-
**Use a tool such as Postman for API testing**. While the custom connector IDE is awesome, it's not meant for API testing. Use a tool such as Postman to test and save the different API requests your custom connector will use. This will rapidly speed up development and testing.

-
**Don't build a custom connector unless it's absolutely necessary**. I know this may sound counterintuitive, but it's the truth. Make sure you explore all other avenues before setting out on the journey to build a custom connector (because believe me, it's a journey). I started development on the Gainsight connector in early December, and it was just published to the AppStore earlier this week. I'd recommend checking out the IDEA Exchange session on Domo's Hidden Gems ([https://www.youtube.com/watch?v=lF4VG8lmEVM](https://www.youtube.com/watch?v=lF4VG8lmEVM)), especially the JSON No Code connector.
