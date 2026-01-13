---
title: "A Diatribe ON Domo's implementation of FIXED functions"
url: /c/articles-and-knowledge-base/a-diatribe-on-domo-s-implementation-of-fixed-functions
author: Jae Myong Wilson
published_date: Dec 12, 2022
updated_date: Dec 12, 2022 at 11:50 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# A Diatribe ON Domo's implementation of FIXED functions
**Author:** Jae Myong Wilson
**Published:** Dec 12, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

---

The FIXED function KB, [https://domohelp.domo.com/hc/en-us/articles/4408174643607-Beast-Mode-FIXED-Functions](https://domohelp.domo.com/hc/en-us/articles/4408174643607-Beast-Mode-FIXED-Functions), fails to differentiate its functionality to WINDOW functions (despite using similar language).

By borrowing from WINDOW function syntax FIXED functions mislead users as to what’s happening under the covers making it difficult to adopt.

This looks like functionality designed to mirror Tableau, but

[https://help.tableau.com/current/pro/desktop/en-us/calculations_calculatedfields_lod_overview.htm
](https://help.tableau.com/current/pro/desktop/en-us/calculations_calculatedfields_lod_overview.htm)

The KB examples duplicate known and well-understood classic Window Function examples but fails to illuminate how Adrenaline is behaving differently under the covers.

SUM(SUM(1) FIXED () ) can be written as SUM(SUM(1)) OVER () … why the duplicate functionality?

Are they arriving at the same result the same way or is there something different about the query execution that retrieves the result?

SUM(SUM(1) FIXED ( BY Region)) can be written as SUM(SUM(1)) OVER (PARTITION BY Region)

Fixed introduces PARTITIOINING without calling it PARTITIONING. Why?

- Does FIXED (BY) operate the same way as OVER (PARTITION BY) -- looks like it.

- It is deeply confusing to see the “BY” recycled without some other word in front.

- In Window functions we have ORDER BY and PARTITION BY

- It might be appropriate (and familiar) to just keep the language of PARTITION BY if it accomplishes the same action OR clearly articulate why they are not the same in the KB.

- Some might argue that there’s a precedence for multiple function implementations that have overlapping functionality ex. DATE_ADD and DATE_SUB. I’d argue that those are well-documented functions and easily understood outside of Domo whereas the concept of FIXED is net new, and the documentation and implied functionality is vague.

**
MAX(SUM(Total SALES) FIXED (ADD City)) Is the first net new piece of functionality.
**

- The ability to subdivide data on a column that is not displayed on the chart is a huge departure from current functionality in Analyzer and Window functions, this is a great addition. – frankly this should just be rolled into WINDOW Function functionality.

- Instead of FIXED(), I would prefer to see ADD added to the set of WINDOW() function parameters.

- Ideally MAX(SUM(total sales)) OVER (ADD City) would accomplish the same thing while recycling our understanding of the WINDOW functions implementation in Domo.

- I would recommend the language of INCLUDE / EXCLUDE instead of ADD / REMOVE because add might imply a mathematical expression (especially if you’re in the context of writing expressions).

**
AVG(AVG(UnitPrice) FIXED (REMOVE ProductCategory))** reads as “the average of an average” which is typically regarded as ‘bad math’ and is NOT what FIXED functions are actually doing.

- This is the heart of my frustration with the implementation / description of FIXED.   FIXED sounds like it’s intended to be calculated before aggregation (the GROUP BY clause), but my ideal state would be to have a version of Window functions that did not require the double aggregation.

﻿
![](https://us.v-cdn.net/6032830/uploads/73F1L1K943H0/image.png)
﻿

WINDOW = AVG(AVG(score)) OVER() = 3.85

- While this is not the result we typically ‘want’, it is mathematically correct (the average of 3 averages)

FIXED = AVG(AVG(score) FIXED () ) = 3.87

- While this is the result we ‘want’, the syntax reads as the “average of an average”.

- The math performed appears to be SUM(allRows) / COUNT(allRows) which should be represented as AVG(score) OVER ()

FIXED functions are misleading

- SUM(AVG(score) FIXED () ) and MAX(AVG( score ) FIXED()) yield the same result.

*
Again --- this is my frustration with FIXED functions. It is not intuitive and does not align with a SQL developer’s understanding of WINDOW functions despite borrowing heavily from that vocabulary. If it’s something different – use different syntax or be VERY explicit in the documentation.
*

**
The REMOVE parameter is AMAZING – but should just be rolled into WINDOW functions
**

- Just like the ALTER tile in Magic ETL allowed me to DROP columns instead of SELECT, the REMOVE parameter allows me to choose the columns I want to exclude from my Partition Window (instead of explicitly enumerating the ones I want to partition by). This makes Window functions more flexible in user-guided analysis because they can alter the axis of a chart without having to rewrite all the WINDOWed beast modes.

- Instead of a FIXED function, I’d rather see REMOVE added to the language of the OVER () clause.

- Ideally, I’d rather see INCLUDE / EXCLUDE instead of ADD/REMOVE because add implies mathematical expression (add vs. subtract).

**
The addition of FILTER NONE and FILTER ALLOW <field> is amazing – but would rather see in a WINDOW function.
**

- For recycled language I’d prefer to see FILTER NONE / INCLUDE / EXCLUDE instead of FILTER NONE / ALLOW / DENY

In conclusion, I do believe the FIXED function introduces net new functionality that would be a huge benefit to WINDOW functions. Given the quality of the explanations provided in the KB, the lack of clarity on what’s actually happening with FIXED functions, and the misleading syntax, I believe it would cause more damage than harm to share this feature with users who have any exposure to SQL.

Originally Posted Here:
[https://dojo.domo.com/main/discussion/55689/fixed-functions-are-difficult-to-understand-and-should-be-rolled-into-window-functions](https://dojo.domo.com/main/discussion/55689/fixed-functions-are-difficult-to-understand-and-should-be-rolled-into-window-functions)
