---
title: "Real-time Red Bull Tracker (in Domo!)"
url: /c/builders-club/real-time-red-bull-tracker-in-domo
author: Elliott Leonard
published_date: Nov 16, 2021
updated_date: Jun 20, 2022 at 05:52 AM
tags: ['Freelancer', 'Master Hacker', 'Admin', 'Domo Sensei']
categories: ['Get Help']
likes: 2
comments: 1
---
# Real-time Red Bull Tracker (in Domo!)
**Author:** Elliott Leonard
**Published:** Nov 16, 2021
**Tags:** Freelancer, Master Hacker, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeVRUSFE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--097ef5386b68fa83df32518d68c8ef016f79f121/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Redbull%20Banner.png)

---

If you know me, then you know I drink way too many energy drinks on a weekly basis 😅 . That's why I decided to create a Domo dashboard for myself to track energy drink consumption (see the public dashboard [HERE](https://public.domo.com/embed/pages/BBjJn)).
﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNWZUSFE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d84eaae4c9c8a55ce0d0ac8fc13cbb23af674cbe/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Screen%20Shot%202021-11-16%20at%2011.18.10%20AM.png)
﻿
The toughest part of this project was figuring out the best way to record when an energy drink was consumed. I settled on using an AWS IoT button (see [HERE](https://www.amazon.com/IoT-Button-AWS-Cloud-Programmable/dp/B0875QVQJW/ref=sr_1_3?keywords=iot+button&qid=1637086151&sr=8-3)) that I attached to the break room fridge. Combine that with Lambda functions (see [HERE](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)) and the Domo Webhook connector (see [HERE](https://www.domo.com/appstore/connector/json-webhook-connector/overview)), and you've got yourself a dataset that refreshes every 15 min!

I love trying to come up with creative data ingestion solutions on Domo. If this post interested you at all, I would highly recommend watching ﻿
[
Jae Myong Wilson
](https://datacrew.circle.so/u/d8050f8c?show_back_link=true)

﻿'s conversation with Andy Beier on Domo's "Hidden Gems" (video [HERE](https://www.youtube.com/watch?v=lF4VG8lmEVM)).

-Elliott
