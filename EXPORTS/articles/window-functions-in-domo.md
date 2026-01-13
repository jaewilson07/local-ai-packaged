---
title: "Window Functions in Domo"
url: /c/articles-and-knowledge-base/window-functions-in-domo
author: Jae Myong Wilson
published_date: Dec 12, 2022
updated_date: Dec 12, 2022 at 11:56 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# Window Functions in Domo
**Author:** Jae Myong Wilson
**Published:** Dec 12, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

---

**Ultimate Guide to Window Functions
**Note:  in mid 2021, Domo silently made changes under the covers to window functions so that they would not allow you to use calculated row-level columns in the OVER() clause, ex. Year(Activity_Date); instead, those calculated columns must be materialized on the dataset (in ETL or dataset view). ﻿

﻿

**Calculating Streaks with Window Functions**﻿

﻿

**The Perils of Lead / Lag with Window Functions**﻿

﻿

### **Why Window functions in Analyzer instead of ETL**

<< placeholder >>

## **Materialized Metrics do not respond to changes in Filter Criteria**

If you implement window functions in your ETL (Rank & Window Tile in Magic 2.0 or window functions in Adrenaline Dataflows), the metrics are fixed and materialized as part of the dataset.  In other words, with materialized metrics, as you apply filters to your cards, the rankings, or cumulative sums will not update.

The only way to have window functions that respond to user interactions on your dashboard or card is via window functions in Analyzer.

## **Why do Beast Modes respond to changes in Filter Criteria**

Analyzer reduces your card to a SQL query that executes at run-time against Domo’s database layer, Adrenaline. Any window functions implemented as beast modes by definition will change according to the data available when the beast mode is evaluated.

## **Window Functions in Dataset Views do not respond to changes in Filter Criteria**

Although window functions in Dataset Views are created in an interface and using a syntax that mirrors beast_modes in Analyzer, window functions implemented in DSVs do not respond to changes in filter criteria applied via cards and dashboards.

Dataset views are SQL queries that are executed against Adrenaline, and their contents do change as the underlying tables they’re built off of update.

Note: It may be helpful as thinking of these Views as the result of a CREATE VIEW AS … command from TSQL.

It is possible to improve View performance by issuing the equivalent of CREATE MATERIALIZED VIEW AS … via a command from the Domo CLI ([kb link](https://domohelp.domo.com/hc/en-us/articles/360043437733-Command-Line-Interface-CLI-Tool)).

### **Performance Implications for Window Functions**

Although Domo may have secret sauce going on under the cover, in general, it’s fair to assume that window functions in DSVs are evaluated when the dataset updates or when the view is defined, and window functions implemented in Analyzer are evaluated at runtime.

This implies that cards that use window functions built into the DSV should render faster than equivalent window functions implemented at the card level.  The major consideration is whether the window functions need to respond to user interactions (filters)

### **Dynamic Segments are a low-code (non beast mode) method of interacting data that spans windows.**

[https://domohelp.domo.com/hc/en-us/articles/4403089503383-Creating-Segments-in-Analyzer](https://domohelp.domo.com/hc/en-us/articles/4403089503383-Creating-Segments-in-Analyzer)

Dynamic Segments fills in gaps in Windowed Beast Mode functionality.  Where Beast Modes focus on creating measures, Dynamic segments allow users to create aggregates of “dimensions”

A Window Function would address “Total Sales by Region”

Whereas a Dynamic Segment would allow users to segment Countries into custom Regions – and then display non-windowed measures by that segment.

Note: the key to understanding Window functions is to understand that Analyzer reduces the card into one query.  Segments and FIXED fucntions; however, issue several queries to Adrenaline.

# **Implemented Functions**

- SUM (*)

- COUNT()

- LEAD()

- LAG()

- AVERAGE (**)

- MIN (**)

- MAX (**)

- RANK (*)

- NTILE() (**)

- PERCENTILE_RANK (**)

Tip: There must be a space between the function and the parenthesis, such as RANK

# **How Domo Implements Window Functions**

In Analyzer each window function must have two aggregates functions.  The first aggregate function tells Domo what to do as it applies the GROUP BY clause (for the axis columns).  The second aggregate function indicates what to do with the rows of data AFTER the GROUP BY clause has been applied.

Consider a table card that shows rowCount by country.

*SELECT *

*Country,*

*sum(1) as RowCount*

*FROM <table>*

*GROUP BY Country*

In standard SQL, window functions ARE NOT ALLOWED in a function with a GROUP BY clause because clause execution order is:

- FROM, JOIN

- WHERE

- GROUP BY

- Aggregate functions

- HAVING

- Window functions

- SELECT

- DISTINCT

- UNION/INTERSECT/EXCEPT

- ORDER BY

- OFFSET

- LIMIT/FETCH/TOP

Domo has a little extra processing that allows us to tack on window functions to a query with a GROUP BY clause by effectively, first processing everything up to the GROUP BY + aggregate functions stage, and then applying windows to result set.

This is why we need the double aggregate functions with window function beast modes.

If you wanted to know the percent of rows across each country you’d need the grand total. In standard SQL we might write:

WITH sub_query as (

*SELECT*

*Country,*

*sum(1) as RowCount,*

*FROM <table>*

*GROUP BY Country*

)

SELECT

Country,

RowCount,

sum(RowCount) OVER () as TotalRows

RowCount / sum(RowCount) OVER () as PercentOfTotal

FROM sub_query

Domo packages this all into one beast mode where we’d write

TotalRows

sum(sum(1)) over ()

PercentOfTotal

sum(1) / sum(sum(1)) over ()

In this example, the inner aggregate, sum(1) says what to do before the GROUP BY clause, and the second aggregation / window is a second query applied after aggregation.

# **Vertica Documentation **

This documentation provides a background into how Window functions actually work behind the scenes and their intended purposes. The documentation is exhaustive and done extremely well. It can help you with ideation and learning what might be possible using these functions:

[https://my.vertica.com/docs/7.1.x/HTML/Content/Authoring/SQLReferenceManual/Functions/Analytic/RANKAnalytic.htm](https://my.vertica.com/docs/7.1.x/HTML/Content/Authoring/SQLReferenceManual/Functions/Analytic/RANKAnalytic.htm)

# **Use Case #1: SUM **

The primary use case for the SUM window function in Beast Mode is an overall total. The general form of the function looks like this:

SUM( <value expression>)

OVER (

PARTITION BY <column separated list of columns>

ORDER BY <column separated list of columns>

)

Note: Ensure there is at least one space between characters in different words; otherwise,  white space is completely ignored, like any other Beast Mode calculation.

## **Understanding the Grand Total Calc**

**SUM( <value expression> ) OVER ()**

When you are actually implementing an overall sum, you’ll typically ignore both the PARTITION BY and ORDER BY parts, leaving you with an empty OVER clause  (just OVER() ). This will get you an overall sum across the entire card. The <value  expression> part can be whatever you’d like to sum up, including any non-window

function Beast Mode formula (or combination of them). However, note that it must be an aggregated value.

## **Understanding other aggregations**

### **SUM( MIN ( ) ) Over ()**

Recall, the inner aggregate defines what happens as the GROUP BY clause is being applied. Consider a dataset that measured the population of several countries each month.

Assume you wrote the beast mode:

sum(min( population)) over ()

You might interpret this as “this was the total population at the beginning of the year;” however that COULD actually be an inaccurate interpretation. What’s happening in SQL?

WITH sub_query as (

SELECT

Country

MIN(Population) as minPopulation,

FROM <table>

GROUP BY

Country

)

SELECT

Country

minPopulation

sum( minPopulation) OVER ()

From

Sub_query

You might assume that the minimum population is at the start of the dataset, but it’s not unreasonable to assume that the population could go down during the year.

Always try to think in terms of aggregation as the GROUP BY is being applied and then what happens next.

### **Careful with COUNT DISTINCT**

It is not possible to capture count(distinct ) over the entire population using Window functions, Beast Modes, or any other tooling in Analyzer.

Consider a dataset of birds, and the countries they have been spotted in.

,

SUM( COUNT(DISTINCT bird_id ) ) OVER()

You might assume that this beast mode would tell you how many different bird types there are across all countries.  But that’s also inaccurate.  One bird species could be native to multiple countries.

Can we COUNT(COUNT(DISTINCT )) .. ?

No.  For each country, after the GROUP BY clause, the data is compressed to one row per country.  So the Count of all rows would be the number of countries in our dataset.

With subquery as (

SELECT

Country,

COUNT(DISTINCT bird_id) as num_species_in_country

FROM <table>

GROUP BY

Country

)

SELECT

Country,

Num_species_in_country,

COUNT(num_species_in_country) OVER ()

FROM subquery

# **Use Case #2: RANK **

The general form of the RANK window function is essentially the same as the SUM function, except that it doesn’t take any parameters in the first set of parentheses. The PARTITION BY and ORDER BY clauses also become important when using rank. Generally, the PARTITION BY clause should only contain the column that you’re using as your primary categorical axis, and the ORDER BY clause should match your card’s sort order.

Note: at the time of this writing you can only include columns in the PARTITION BY clause that actually exist in the dataset (i.e. you cannot use MONTH(activity_date) in a window function.

Additionally, you can only use columns in the PARTITION BY or ORDER BY clause that are included on one of the axes of the card.

Here are a few examples:

## **Understanding Partition By**

Consider a dataset of deals closed and the sales rep associated with each deal.  A rep could have one or many deals.

Assume we have a table with the rep, and sum(revenue)

SELECT

Rep,

sum(revenue) as rep_revenue

FROM <table>

GROUP BY
Rep

If we add

RANK() over ( ORDER BY SUM(revenue) desc )  for each Rep we’d calculate their rank compared to other reps.

The PARTITION BY clause effectively says “subdivide my window.”  So if we add

RANK() over ( PARTITION BY rep ORDER BY SUM(revenue) desc ), we’d be saying “reset the ranking for each rep.  The end result would be 1 for each rep.

If we added Region to the table,

SELECT

Rep,

Region,

sum(revenue) as rep_revenue

FROM <table>

GROUP BY
Rep,

Region

And then wanted to Rank each rep within their region, now the PARTITION BY clause makes sense

RANK() over ( PARTITION BY Region ORDER BY SUM(revenue) desc ), we’d now have rep ranking within each region.

# **Use Case #3: Percentile Rank and  N-tile **

## **Understanding Percentile (aka Percent_Rank)**

A Percentile captures a value on a decimal scale between 0 to 1 that indicates the percent of a distribution that is equal to or below it.

Let’s say you have a dataset of employees and their salaries.  The .95 percent_rank() indicates that 95% of the employees make that salary or less.

Keeping in mind that Domo requires double aggregation … so we couldn’t actually capture the above example in a Domo card because there is no reasonable candidate for double aggregation (you’d just implement the above in ETL)

Consider a survey of cities where each city is ranked between 1 and 100 on a variety of metrics.  Your dataset is shaped <country>, <city>, <metric>, <score>.

If you wanted to compare cities, you might start with avg_score and the percent_rank().

SELECT

City,

Country,

avg(score) as avg_score

FROM <table>

GROUP BY

Country,

If Seoul had an avg_score of 67 and a .5 percent_rank, percent_rank() over( order by avg(score)), that would indicate that 50% of cities had an average score of 67 or lower.

Percent_Rank provides a way of comparing entities abstracted from the actual score.  Typically we’d say “oh a 67 is barely passing”, but if 50% of the population is 67 or lower, that allows us to focus on a comparison of the cities and not necessarily their performance in the metrics.

Partitioning by Date or Country would provide more granular analysis if appropriate.

## **Understanding NTile**

Keeping with our previous example of a dataset of <country>,<city>, <metric>, <score>

Where percent_rank() returns a continuous score between 0 and 1, NTILE makes it easier to graph results by grouping the score into discrete buckets.

NTILE(5) over (ORDER BY avg(score)) would assign a score between 1 and 5 to each city.

If there were 20 cities,  each bucket (1 through 5) would contain 4 cities, and each city in that bucket would be between the 1 to 20th, 20th to 40th 40th to 60th percentile.

# **Use Case #4: Running Totals (a.ka. Cumulative Sum)**

Use the same approach as the Grand Total, but introduce an ORDER BY clause.

Assume we have a table

SELECT

activity_yearMonth,

sum(revenue) as monthly_revenue

FROM <table>

GROUP BY

activity_yearMonth

If we want to track the cumulative sum, we’d introduce the same SUM(SUM()) window function from before but with an ORDER BY clause.

SUM(SUM(revenue)) OVER (ORDER BY activity_yearMonth asc)

Note: recall, we any field we’d like to use in the ORDER BY or PARTITON BY clause must be on one of the card Axes.

If you want to reset your cumulative sum each year, you must include activity_year on the axis.

SELECT

activity_yearMonth,

activity_year,

sum(revenue) as monthly_revenue

FROM <table>

GROUP BY

activity_yearMonth

activity_year

Now we can add the beast mode:

SUM(SUM(revenue)) OVER (PARTITION BY activity_year ORDER BY activity_yearMonth asc)

# **Use Case #5: LEAD and LAG**

Lead and Lag only apply for data that actually exists in the result set.

Beast Mode Syntax:

LAG( <value_expression> , <rows_to_lag> ) OVER (ORDER BY <column> )

## **Be cautious of using LEAD / LAG in Period-over-Period Comparison**

Prior to the release of Variables feature, a common solution for period-over-period comparison was to use LEAD / LAG to cross contexts.

Consider the table

WITH subquery as (

SELECT

activity_yearMonth,

sum(amount) as amount_month

FROM <table>

GROUP BY

activity_yearMonth

)

Select

activity_yearMonth,

amount_month,

lag(amount_month, 1) over (ORDER BY  activity_yearMonth asc ) as lag_1,

lag(amount_month, 2) over (ORDER BY  activity_yearMonth asc ) as lag_2

FROM

Subquery

Assume we’ve added a filter, WHERE Prod_id = ‘abc’, using a QuickFilter interaction.

A user might interpret lag_1 as “the amount from the previous month”; however that’s only true if there was activity in the previous month.

Assume we are in August and prod_id ‘abc’ was nearing end of lifecycle.  There were sales in May, June, Aug but not July.  With lag(1), we may assume that lag_1 represents July when in fact lag_1 would represent the next available month, June.

# **Filters and Window Functions**

## **Filtering on the WHERE clause**

Domo follows the execution order of SQL Queries.

- FROM, JOIN

- WHERE

- GROUP BY

- Aggregate functions

- HAVING

- Window functions

- SELECT

- DISTINCT

- UNION/INTERSECT/EXCEPT

- ORDER BY

- OFFSET

- LIMIT/FETCH/TOP

Notice that the WHERE clause is applied before the GROUP BY and WINDOW clause are evaluated.

In Analyzer, when we apply a filter using DateFilters, Quick Filters, or just ‘normal’ Filters, those are applied as a WHERE clause.

If we used the analyzer interface to apply a filter, it will (usually) apply as a WHERE clause.

SELECT

activity_yearMonth,

activity_year,

sum(revenue) as monthly_revenue

FROM <table>

WHERE Country = ‘USA’

GROUP BY

activity_yearMonth

activity_year

We would expect no mention of any other country in our card.

## **Filtering on the HAVING clause**

Domo has extended functionality (via Feature Switch) to allow filtering on the HAVING clause.

Assume our dataset has <country>, <city>, <metric>, <score>

Typically  “filtering on the having clause” means filtering on an aggregated value.  If we wanted to only show Countries with an average score greater than 50, we would be asking to apply a filter after aggregation.

There is a material difference between

FILTER on WHERE | FILTER on HAVING
SELECTCountry avg(Score) as avg_score FROM CountryWHERE score > 50GROUP BY Country
| SELECTCountry avg(Score) as avg_score FROM CountryGROUP BY CountryHAVING avg(Score) > 50

In Analyzer, if you filter on a beast mode, you will be applying the filter using a HAVING clause.

The end-user experience between filtering on HAVING versus filtering on WHERE is seamless (it all happens in the same places in the UI); however, from the perspective of understanding Domo, it is important to recognize what is happening so users can predict behavior

## **Why you cannot filter on a WINDOW function**

You should not / cannot filter on the result of a WINDOW function.

Review the order of SQL clause execution to understand why it is not possible.

Keep in mind, Domo is reducing your Analyzer card into a SQL query.  Filtering removes data from the result set.  If you Filtered on a Window (let’s say RANK), that would shift the rank of the remaining result set.  You’d have an infinite loop.

### Related Articles

On Fixed Functions﻿

[

](#remove-attachment)

[

The FIXED function KB, https://domohelp.domo.com/hc/en-us/articles/4408174643607-Beast-Mode-FIXED-Functions, fails to differentiate its functionality to WINDOW functions (despite using similar language).
By borrowing from WINDOW function syntax FIXED ...

https://datacrew.circle.so/c/articles-and-knowledge-base/a-diatribe-on-domo-s-implementation-of-fixed-functions

](https://datacrew.circle.so/c/articles-and-knowledge-base/a-diatribe-on-domo-s-implementation-of-fixed-functions)

﻿
On Implemented Adrenaline functions
﻿

[

](#remove-attachment)

[

Note this is not a comprehensive list nor is it 'official'.

If you are unable to use a specific function in your implementation contact your CSM.  For example Median is not enabled out of the box.

Note most SQL-esque function implementations in Domo ...

https://datacrew.circle.so/c/developerdomocom-community-edition/supported-functions-in-adrenaline-dataflows-views-and-beast-modes

](https://datacrew.circle.so/c/developerdomocom-community-edition/supported-functions-in-adrenaline-dataflows-views-and-beast-modes)

﻿
