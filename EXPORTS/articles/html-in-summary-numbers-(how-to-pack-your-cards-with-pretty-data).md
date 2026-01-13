---
title: "HTML in Summary Numbers (how to pack your cards with \"pretty\" data)"
url: /c/builders-club/html-in-summary-numbers-how-to-pack-your-cards-with-pretty-data
author: Elliott Leonard
published_date: Nov 1, 2021
updated_date: Jun 20, 2022 at 05:50 AM
tags: ['Master Hacker']
categories: ['Get Help']
likes: 2
---
# HTML in Summary Numbers (how to pack your cards with "pretty" data)
**Author:** Elliott Leonard
**Published:** Nov 1, 2021
**Tags:** Master Hacker
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNFBqR3c9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--9d7bbdf13709416ba441419c1b6ff81ffb6c86ef/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/domo-vector-logo.png)

---

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBOVBqR3c9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--139f09538e3a308d589abc5f7aa73fb1beadb621/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Screen%20Shot%202021-11-01%20at%209.41.15%20AM.png)
﻿When I figured out a couple of weeks ago that you could inject HTML into summary numbers in cards, it absolutely blew my mind! Since then, I've been trying to find creative ways to add this to my client work, since so many customers are asking for more data-rich cards.

In this example, I wanted to show the current laptop market share for 2021, while at the same time showing how Apple is gaining market share compared to previous years. I was able to accomplish this using a beastmode, CONCAT function, HTML table element, and some simple CSS styling.

You can find this example on the Dojo instance here: [https://domo-dojo.domo.com/page/-100000/kpis/details/677960202](https://domo-dojo.domo.com/page/-100000/kpis/details/677960202) **(if you don't have access, talk to Jae or bvk)**

Or, if you're lazy like me, you can take a look at my beastmode here:

CONCAT('<table > <tr> <th style="background-color:#D9EBFD">Apple 2020</th>
<th style = "background-color:#E8E8E8">Apple 2019</th></tr>',
'<tr>','<td style="background-color:#D9EBFD">',concat('<div style="font-weight:bold;color:green">','▲ ',round(((sum(case when `Year` = 2021 and `Company` = 'Apple' then `Market Share` else 0 end))-(sum(case when `Year` = 2020 and `Company` = 'Apple' then `Market Share` else 0 end)))*100,2),'%'),'</td>',
'<td style="background-color:#E8E8E8">',concat('<div style="font-weight:bold;color:red">','▼ ',round(((sum(case when `Year` = 2021 and `Company` = 'Apple' then `Market Share` else 0 end))-(sum(case when `Year` = 2019 and `Company` = 'Apple' then `Market Share` else 0 end)))*100,2),'%','</td>','</tr>','</table>'))﻿
---
﻿
I'm no HTML expert, but just imagine all the possibilities here!! What are some cool things you could do with this?? Would love to hear your thoughts in the comments.

-Elliott
