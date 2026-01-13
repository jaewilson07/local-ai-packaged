---
title: "How to describe a Problem // Consulting vs. Support"
url: /c/consulting-resources-and-professional-development/how-to-describe-a-problem-consulting-vs-support
author: Jae Myong Wilson
published_date: May 17, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Consulting Resources &amp; Professional Development']
---
# How to describe a Problem // Consulting vs. Support
**Author:** Jae Myong Wilson
**Published:** May 17, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Consulting Resources &amp; Professional Development

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNk1GREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--78a2b03e0078ad69d7b5da30f15482cd9a9eb0be/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/3.png)

---

When asking for help (from [support@domo.com](mailto:support@domo.com), from a fellow consultant, or in any technical community), be aware of the distinction between asking for help and asking for consultation.

> Support or community help is generally expected to be free whereas consulting typically comes with monetary exchange because it requires more investment in understanding your use case.

> My rule of thumb:  "don't ask support questions that you can't google in a well documented Knowledge Base."

At a previous company I worked for, there was an actual [KB article](https://support.jetglobal.com/hc/en-us/articles/219402767-Guidelines-Regarding-Support-Versus-Billable-Work) that differentiated between Tech Support and Billable Services.

### What is Considered Technical Support?

Some topics that are considered to be technical support issues are:

- Questions about software compatibility and hardware requirements

- Issues regarding connector configuration

- Help with Error messages

### What is Considered a Billable Consultation?

Questions regarding report design are usually considered a billable consultation.   These are outside the scope of technical support as they are not related to the technical software issues but rather related to training and consulting ...  Inquiries that can be resolved quickly will not generally be considered billable.  Some topics that are considered to be a billable consultation are:

- Questions on how to design a report

- Questions about how to structure data

## Considerations for Business Consultants & Major Domos.

> BCs and Major Domos should generate documentation that doesn't require a phone call for the technical developer to begin developing a solution.  Ideally one should assume that BCs and TCs are operating asynchronously.

> My rule of thumb:  If I can answer your question in a 5-minute email that's free of charge.  But if I have to get on a phone call, I have to bill you for the time.

Developing a shorthand or playbook of design patterns may help simplify the technical documentation process.

## Core elements to communicate.

Although it's no substitute for words, a screenshot or ideally sample dataset is worth a thousand words.

> Screenshots or sample data allow developers to confirm, understand and/or challenge your assumptions about granularity (but they are not a substitute for a statement of the problem / or your expectations of granularity.)

**What is the current behavior?  What is the delta to the expected behavior?**

"How do you know this is wrong?" AND "how will you know when it is right"

###
**What is the **[**granularity **](https://stackoverflow.com/questions/39181036/whats-the-grain-in-the-context-of-dw)**of the data (desired vs expected)**

What does one row in the table represent? how do you identify a row?

- Misalignment of Data Granularity is the leading problem in errors after ETL execution.

- Performance problems in Analyzer or overly complex Beast Modes are problems frequently associated with data modeling inefficiencies.

### Frame your question appropriately for the context -- support vs. consulting

With support:  Abstract away the unnecessary backstory and just provide enough information so we can get you unblocked.  Remember, support should solve a technical problem, not be expected to give good advice.

For Consulting / Project Documentation / Requirements Gathering: supply sufficient information for a technical resource to develop a solution that both addresses the requirement as well provide an optimal solution.  Considerations include:

- how often the pipeline should update

- expected data volume

- who will maintain the dataflow

"Can you debug this code... " -- Ideally, you will get the answer to your question because it is very specific; however, if you don't provide the larger context of what you're trying to accomplish you may miss the opportunity for a consultant to tell you a more efficient solution to your problem.

ex.  "How can I make this MySQL dataflow run faster." Indexing is usually the answer.  But an even better solution might be to reimplement in Magic 2.0 or even better using Dataset Views.
