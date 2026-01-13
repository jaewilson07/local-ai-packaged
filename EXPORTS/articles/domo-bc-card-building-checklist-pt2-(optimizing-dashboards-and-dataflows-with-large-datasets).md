---
title: "DOMO BC - Card Building - Checklist Pt2 (Optimizing Dashboards and Dataflows with large datasets)"
url: /c/consulting-resources-and-professional-development/card-building-checklist-pt2-optimizing-dashboards-and-dataflows-with-large-datasets
author: Jae Myong Wilson
published_date: May 12, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Consulting Resources &amp; Professional Development']
---
# DOMO BC - Card Building - Checklist Pt2 (Optimizing Dashboards and Dataflows with large datasets)
**Author:** Jae Myong Wilson
**Published:** May 12, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Consulting Resources &amp; Professional Development

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNDBFREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--65f34d2d022be8522b5d2190815668e2e42bcd63/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/3.png)

---

## General Info

- Box Plots and Histograms have a limit of 100,000 rows of data. Other chart types have a limit of 25,000 rows (although the charting engine may limit the data further depending on how many series are represented).

- Sumo Tables only preview a subset of the data instead of Table cards which load as many as 500 rows

- Card Building FAQ: [https://knowledge.domo.com/Visualize/Adding_Cards_to_Domo/KPI_Cards/KPI_Card_Building_Part_2%3A_The_Analyzer/Card_Building_FAQs](https://knowledge.domo.com/Visualize/Adding_Cards_to_Domo/KPI_Cards/KPI_Card_Building_Part_2%3A_The_Analyzer/Card_Building_FAQs)

## Some tips for approaching visualisation (normal datasets)

- Think about the level of granularity required

- For the Summary Number, check you are using the right aggregation type. For example, the "Current" aggregation is most appropriate for chart types with a trendline.

- Limiting your number of Collections to roughly 3-5 Collections per page is ideal for navigation and information consumption.

- Remove "Auto Preview" from Analyzer to avoid having the preview to load while building the card

- Avoid reporting on dateTime columns unless absolutely necessary

instead separate date and time into separate columns.

- by separating date and time, can leverage a dimension table to attach time and date attributes (Year, Month, or Morning, Afternoon)

- high cardinality reduces the efficiency of columnar indexing. (which impacts FILTER performance, JOINS etc

## Visualizing Semi-additive facts

> Many connectors / reports will include semi-additive facts which cannot be aggregated (typically across the time dimension).

These datasets should be carefully shaped to avoid misuse/misinterpretation of data

- Consider a dataset of Bank Statement Balances.  You could not take the sum(balance) column.

- Dimension tables with aggregate metrics make it difficult to provide trend reporting or understand KPIs in context

Consider taking snapshots of the customer dim table state (data assembler) to create a semi-additive fact table OR uploading the transactional table

### Additional Resources

- [https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/)

## Domo Q&A  - Optimizing Dashboards & Dataflows with large data

During a 1:1 mentoring session, I gave a consultant some tried and tested methods for optimizing dashboard and card performance against large datasets.

﻿

﻿

### Quick Tips for Developer Experience in Analyzer

- Remove "Auto Preview" from Analyzer to avoid having the preview to load while building the card

- In Analyzer, apply filters to the card before applying dimensions or measures to the Axis.

Apply filters from large to small: Country → Region → City

- Apply time period filter (Current year, Today...)

- Apply row limit to the Data table (useful for Top 10)

- Make sure the visualisation granularity is not too high (remember 25,000 points)
In Date, apply a date granularity (None → Day → Month → Year) -- avoid the use of DateTime columns.

- Use beast modes saved to the dataset or materialized columns to aggregate by month or year instead of relying on card layer beastmodes, (b/c Adrenaline cannot cache results)

- Remove unnecessary Sorts

- Avoid / minimise use of count(distinct) consider approximate_count_distinct
[https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AnalyzingData/Optimizations/OptimizingCOUNTDISTINCTByCalculatingApproximateCounts.htm](https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AnalyzingData/Optimizations/OptimizingCOUNTDISTINCTByCalculatingApproximateCounts.htm)

COUNT(DISTINCT(`Measure`))
VS
APPROXIMATE_COUNT_DISTINCT ( expression[, error-tolerance ] )

### Create a data-exploration Page instead of using Analyzer

- Filters can be made out of smaller dimensional datasets and therefore load values faster than in Analyzer

- Use a Pivot Table or Sumo Card to explore the data

- Use Dataset Views to explore data at the row level

[Part 1](https://datacrew.circle.so/c/articles-and-knowledge-base/card-building-checklist)
