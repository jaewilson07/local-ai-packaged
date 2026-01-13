---
title: "Prequel.ai // App clone // Scaling Internal Knowledge"
url: /c/builders-club/prequel-ai-app-clone
author: Jae Myong Wilson
published_date: Jun 14, 2021
updated_date: Jun 20, 2022 at 05:30 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# Prequel.ai // App clone // Scaling Internal Knowledge
**Author:** Jae Myong Wilson
**Published:** Jun 14, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

---

[https://www.prequel.ai/](https://www.prequel.ai/)
Does anyone want to build an app that is kind of like Jupyter Notebook, but intended to document research in Domo?

Check out this super cool article
[Scaling knowledge at AirBnb](https://medium.com/airbnb-engineering/scaling-knowledge-at-airbnb-875d73eff091)

### Five key tenets for what we wanted in our DS research:

-
*Reproducibility* — There should be no opportunity for code forks. The entire set of queries, transforms, visualizations, and write-up should be contained in each contribution and be up to date with the results.

-
*Quality* — No piece of research should be shared without being reviewed for correctness and precision.

-
*Consumability* — The results should be understandable to readers besides the author. Aesthetics should be consistent and on brand across research.

-
*Discoverability* — Anyone should be able to find, navigate, and stay up to date on the existing set of work on a topic.

-
*Learning* — In line with reproducibility, other researchers should be able to expand their abilities with tools and techniques from others’ work.

### Ensuring High Quality Research

Unlike engineering code, low quality research doesn’t create metric drops or crash reports. Instead, low quality research manifests as an environment of knowledge cacophony, where teams only read and trust research that they themselves created.

﻿
![](https://miro.medium.com/max/882/1*MPdpSg36RzBeinrL0wIGwQ.png)
﻿
To prevent this from happening, our process combines the code review of engineering with the peer review of academia, wrapped in tools to make it all go at startup speed. As in code reviews, we check for code correctness and best practices and tools. As in peer reviews, we check for methodological improvements, connections with preexisting work, and precision in expository claims. We typically don’t aim for a research post to cover every corner of investigation, but instead prefer quick iterations that are correct and transparent about their limitations. Our tooling includes internal R and Python libraries to maintain on-brand, aesthetic consistency, functions to integrate with our data warehouse, and file processing to fit R and Python notebook files to GitHub pull requests.
﻿
![](https://miro.medium.com/max/882/1*oib1FYv2tb3vFBsbdKIMKg.png)
﻿

Together, this provides great functionality around our knowledge tenets:

-
*Reproducibility *— The entirety of the work, from the query of our core ETL tables, to the transforms, visualizations, and write-up, is contained in one file, the Jupyter notebook, RMarkdown, or markdown file.

-
*Quality *— By leaning on GitHub’s functionality of pull requests prior to publishing, peer review and version control is put directly into the flow of work.

-
*Consumability *— The markdown served by our web-app hides code and uses our internal branded aesthetics, making the work more accessible to less technical readers. The peer review process also provides feedback on writing and communication, which improves the impact of the work.

-
*Discoverability *— The structured meta-data allows for easier navigation through past research. Each post has a set of tags, providing a many-to-one topic inheritance that goes beyond the folder location of the file. Users can subscribe to topics and get notified of a new contribution. Posts can be bookmarked, browsed by author, or perused as a blog feed.

-
*Learning* — By having previous work easily accessible, it becomes easier to learn from each other. For example, one can review each other’s queries, see the code used for a creative visualization, and discover new data sources. This exposes Data Scientists to new methodologies and coding techniques, speeds up on-boarding, and makes it possible for people outside our team to learn about our field.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeDB2RGc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--5d42bc11da8ba966c92f0d777b97ee42a2c89c3b/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/query.png)
﻿

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeDh2RGc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--0c8bffed661a6b01bd89b5f666f59b765f6a813c/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/query.png)
﻿

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeUF2RGc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--ae79bbf65bd7133be8e30d794d04db19d4b8059e/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/query.png)
﻿
