---
title: "5/24 - Cool Stuff Digest"
url: /c/articles-and-knowledge-base/5-24-cool-stuff-digest
author: Jae Myong Wilson
published_date: May 25, 2021
updated_date: Nov 26, 2022 at 10:55 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# 5/24 - Cool Stuff Digest
**Author:** Jae Myong Wilson
**Published:** May 25, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMStsREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d76ff84aeb486a51ad37456e3c6c39ecd7c1b5bb/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/Luma%20(2).jpg)

---

## Food for Thought // Is the 🧰 Data Warehouse Toolkit ⚰️ Dead?

- In the era of GCP, Azure, and Datalake infrastructure, processing power has trivialized the performance benefits Ralph Kimball laid out in his [Data Warehouse Toolkit](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/books/data-warehouse-dw-toolkit/).

- If you don't know Ralph Kimball and you're a BI developer, I recommend the book very strongly.

If you're not familiar with Dimensional Modeling in the context of Business Intelligence development, regardless of whether you feel the techniques are dated, IMHO, Kimball's texts are the gold standard for data warehouse design.

### Domo is a bit different.

SQL developers initially struggle with Domo because although it does have a very performant database layer (Adrenaline) data pipelines are generally not set up in a way where you can ALTER, INSERT, UPDATE, or DELETE rows or tables stored in the database layer.

By default, all data loaded into Domo is either a full replace (DROP, BULK INSERT) or a straight APPEND.  Domo does support UPSERT during the ingest phase but not on data transformed in ETL pipelines.  Therefore, many of the tools and patterns we'd rely on from Kimball aren't really available in Domo's preferred transformation tools: primary and foreign key relations, schemas etc.

This brings me back to my original question.  Is Kimball's Data Warehouse Toolkit dead?  Should people continue to learn the design patterns so as to have a foundation to adapt in a data lake environment?

[https://www.holistics.io/blog/scd-cloud-data-warehouse/](https://www.holistics.io/blog/scd-cloud-data-warehouse/)

## A note on Nested CASE Statements

I saw this in a project I was reviewing:

CASE
WHEN (`Data Source` = 'Stuff') OR (`Data Source` = 'More Stuff') THEN  0
ELSE
CASE
WHEN `Data Source` like '%stuff%' AND `Sales`=0 THEN 0 ELSE `First Cost` *`NetUnits` END
END
Let's avoid nested CASE statements.  On paper, they are syntactically fine, in execution, it makes it difficult to understand what logic is being applied when.

Consider this alternative.  🧽So clean! 🛀

CASE
WHEN `Data Source` IN ( 'Stuff' , 'More Stuff') THEN 0
WHEN `Data Source` like '%stuff%' AND `Sales`= 0 THEN 0
ELSE `First Cost` *`NetUnits` END
END
Personally I don't like the setup of this CASE statement because it puts the exceptions first ("if it's this then zero, if it's that it's zero, otherwise it's ... math ... ").

CASE
WHEN `Data Source` NOT IN ( 'Shopify Discounts' , 'Shopify Price Adjustments') AND (`Data Source` not like '%Shopify%' AND `Sales`=0 )  THEN  `First Cost` * `NetUnits` END
In the second variant, I like that there's no ELSE 0.  Because there's a ...

## Difference between NULL and 0

One should be very careful about writing 0 into a metric column.

// UNIT PRICE
CASE
WHEN `NetUnits`= 0 Then 0
ELSE `Sales` / `NetUnits`
END
First off, logically this is backward. Don't lead with exceptions.
If you had to explain Unit Price to someone you'd say, "Unit price is ... math... except when ..."

**** on most days of the week you should not write ELSE 0 into your metrics ****

Mathematically, this code makes sense, you cannot divide by 0, so we're implementing logic to avoid the DIV/0 error.
But from the Business Logic perspective. This math is both obtuse and potentially wrong.

✔️ Solution ✔️

// v1
CASE
WHEN `NetUnits <> 0 then Sales / NetUnits  ELSE NULL
END
// v2
CASE
WHEN `NetUnits <> 0 and `NetUnits` IS NOT NULL then Sales / NetUnits
ELSE Sales
END
Are we just splitting hairs?
There is a difference between 0 and NULL.
The original beast mode can be interpreted as:
"If I sold 0 units then I sold a unit for 0 dollars."

That's wrong. But only when you turn it around: "I had a sale for zero dollars therefore i sold 0 units."
1) You COULD sell 1 Unit for 0 dollars (buy one get one free. or an employee discount. or a sweepstake.)
2) You COULD sell something that is not measured in units. On invoices you can sell services, shipping fees, or rebates. Depending on the system,  NetUnits could be 0, 1 or NULL.

### Mathematical difference between 0 and NULL revisited.

If I had 3 lines of activity with unit price 5,5 and 0; the average unit price is 3.33.
If I had 3 lines of activity with unit price 5, 5, null; the average unit price is 5.
