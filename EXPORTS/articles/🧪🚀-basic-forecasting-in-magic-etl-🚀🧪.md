---
title: "🧪🚀 Basic Forecasting in Magic ETL 🚀🧪"
url: /c/developerdomocom-community-edition/basic-forecasting-in-magic-etl
author: Jae Myong Wilson
published_date: Oct 3, 2022
updated_date: Nov 26, 2022 at 10:53 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# 🧪🚀 Basic Forecasting in Magic ETL 🚀🧪
**Author:** Jae Myong Wilson
**Published:** Oct 3, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Why do we do Forecasting?  To predict the future.

FOLLOW-UP QUESTION (that we always forget to ask).

🔮🎴 How good are we at predicting the future? 🔮🎴

Free YouTube Full Tutorial﻿

﻿
** note, my video won't show you how to make a "good" forecast, or "performance tune" your forecast.  Instead it focuses on how you should consider structuring your data in Domo.  Which forecasting model you use is up to you, you could try rolling 90, rolling 30, naive etc.

How do you know which forecast to use?  Check out the segment where I talk about Cost Equations.

## CRITICAL CONCEPTS

## Unit of Analysis

Forecasting applies “crazy math” to a dataset to predict “the next row of data”

- The INPUT must be at the same granularity as the OUTPUT

Aggregate your Data to the same granularity.  If the data is at the transactional level, use a GROUP BY tile.﻿
![](https://lh5.googleusercontent.com/HFAPOvReK6H3zV2c7V9x281fBcMJPhLmmY7truQr-wuSuTG9WCVmzqCRYLEhUtFRfBrtqFUdoDzHv6zfIKgKjkKVyclmVkyiomS48MNbV9l6QJs7c6NKlor0q30zifpA03jbL_oYPd7wZ0UapwlJHGJSqS2uVLLVIeY1WH8qfn-EzgmsvLxCXk-eGQ)
﻿ ﻿
![](https://lh3.googleusercontent.com/YJdXwrzllWVk8mRC22GeBSaeSX4rni5MLttesJodjzv74VGN2qF0CLoPaJPYPwYfXRJ8NcheOcsOGWhSWltXP5nr5kUI6-DoCE4VnlrFZj4cDhFDNGo2rmwhtYrN1TWDAQbk5PrjzD0hbinkcGqQ-cNCo80m2IbB8EHFh9jYS5ye25I7flEtY_ycAg)
﻿

### CATEGORICAL DATA vs. NUMERIC DATA

The model does not understand “concepts” or “categories”.

- The model reduces the world to numbers.  (even categories get converted to numbers)

- Some Data models support ORDERED columns // many do not.

- Some columns are discrete (bucketed) others are not.

- Some columns have boundaries or exist on a scale (temperature, percentage) others do not (sales price, distance)

Generate one Forecast Tile for each categorical variable combination (ex. Stores and items)
You MUST GROUP BY | ﻿
![](https://lh3.googleusercontent.com/M_JEhZr-ZOn4CiLlvDfelsFV0sMHw0VvBB-EpmraE-KktFkEmcJvungcIwtIAF1UXn8F0EmYBEqf4RSts20XZCXThJr9rdWQ0kxfiBYo0jZQDzw6Ul0bL9TAcWhbwBTuHxos76hfFOumuKOnrTH6ve8dKrmaed4wgvqO1dRNbx74S6wY-WArfi8jWw)
﻿

## Increase the Accountability of your Forecast Model

1. Use multiple flows (Offset = 7, 14 or 21) to capture the historical forecast
﻿
![](https://lh6.googleusercontent.com/BrME0sF2hyuqpvt4oHO59fwVUN2zsT3AQtKhh6yMTItln4wusHHl43AVaQQu-FZ7kg_6Ine2RBoefLhwStP0d0JMc0B0GjDldVo3kYHGB4muCqN44rTn6YqKEPTaBdrAUSNnJUSi7Mlbmk53jL0yAyIwtjb_JQXs9Ma1_D3L998aMQd7KP3u0M5QwQ)
﻿
2. JOIN actuals onto the predictions so you can calculate absolute error or a cost equation to ascertain "how bad" your prediction was.

3. Consider comparing previous forecasts (with the WINDOW function) | ﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNzY0YXc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--2202cfba92b6f85992bdc2396245119e39bb83c3/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJVUU1SEJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--2ed767da9d356849cc629c62190b1d347052fee7/Capture.PNG)
﻿
GOOD LUCK!
I've covered some best practices before in this video
[https://www.youtube.com/watch?v=lhj9zcwai98](https://www.youtube.com/watch?v=lhj9zcwai98)

And actually have an entire channel about Data Science
[https://www.youtube.com/watch?v=_UGd0Ug9D5M&list=PLUy_qbtzH0S6HKLlz_MG_gRH2VKhi36sW](https://www.youtube.com/watch?v=_UGd0Ug9D5M&list=PLUy_qbtzH0S6HKLlz_MG_gRH2VKhi36sW)

Questions?  Join the Domo Slack Community
[https://join.slack.com/t/domousergroup/shared_invite/zt-1fo623tm8-dUAf6Aq6vNOG1ad79BueyA](https://join.slack.com/t/domousergroup/shared_invite/zt-1fo623tm8-dUAf6Aq6vNOG1ad79BueyA)

Want to view the ETL? Jump into the Domo-Dojo sandbox
[https://domo-dojo.domo.com/datacenter/dataflows/102/graph](https://domo-dojo.domo.com/datacenter/dataflows/102/graph)
