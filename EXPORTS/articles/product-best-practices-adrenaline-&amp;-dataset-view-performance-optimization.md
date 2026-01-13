---
title: "PRODUCT BEST PRACTICES // Adrenaline &amp; Dataset View Performance Optimization"
url: /c/articles-and-knowledge-base/adrenaline-dataset-view-performance-optimization
author: Jae Myong Wilson
published_date: May 13, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# PRODUCT BEST PRACTICES // Adrenaline &amp; Dataset View Performance Optimization
**Author:** Jae Myong Wilson
**Published:** May 13, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBK3dXREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d57b0795ec4e6159edcd81b3517b1519245bdfa7/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/6.png)

---

At the [Domo IDEA Exhange](https://www.onyxreporting.com/conference) Nihar reviewed three core components of Domo architecture, durable storage in Vault, the Adrenaline query engine, and data transformation tools.

Over the past two years, Domo has developed new tools for building more efficient and performant dataflows including Magic 2.0, Dataset Views, and Adrenaline Dataflows.  USE THEM!
﻿

﻿

# What is a Dataset View / DataView / Fusion?

Dataset Views, DataViews and Fusions are synonymous.

> Views, Fusions and DataViews are generated via java CLI, Data Grid views (beta) and Fusion UI exist in the same piece of Domo's Architechture, the database layer, Adrenaline.

They're 'just SQL Views'  conceptually equivalent to

CREATE VIEW [Brazil Customers] AS
SELECT CustomerName, ContactName
FROM Customers
WHERE Country = "Brazil";

### When do views update?

By default, a view will re-index automatically (in Adrenaline) when the input datasets are updated.

- Input datasets must finish indexing before a view can process

- this action will clear the cache, so all queries run cold (a little slower) until the cache warms up

- Support / Engineering Services can disable the automatic updates of a Fusion (requiring manual indexing)
use the index-dataset command from the JavaCLI

### On Materialized Views

CREATE MATERIALIZED VIEW [Brazil Customers] AS
SELECT CustomerName, ContactName
FROM Customers
WHERE Country = "Brazil";

Materialized views are treated like normal datasets (get backed up in Vault AND have disaster recovery etc tooling around them, whereas normal views only exist in the Adrenaline layer.

### On Dataview Optimization // Jeremy K (25/3/2020)

If query performance is poor, Engineering via [support@domo.com](mailto:support@domo.com) can be engaged for optimization efforts provided the guidance available in KB articles has been followed:

- [https://knowledge.domo.com/Prepare/DataFlow_Tips_and_Tricks/DataFlow_and_DataFusion_Troubleshooting_and_FAQ](https://knowledge.domo.com/Prepare/DataFlow_Tips_and_Tricks/DataFlow_and_DataFusion_Troubleshooting_and_FAQ)

- [https://knowledge.domo.com/Prepare/Magic_Transforms/DataFusion/DataFusion_Performance_Recommendations](https://knowledge.domo.com/Prepare/Magic_Transforms/DataFusion/DataFusion_Performance_Recommendations)

Support / Engineering will then assess and implement the appropriate backend optimization techniques.

### What kind of schema changes would cause the optimizations to break resulting in Support / Engineering needing to re-optimize the view?

- Optimizations the DBAs make will not break with schema changes, although they could potentially become ineffective. If we have optimized for a certain column filter and the customer stops filtering on that column, for example, the optimization would no longer provide benefit.

- The DBA team optimizes datasets only via requests submitted via Support (provided they have been optimized according to best practices).

### Do we have the same restrictions around schema changes for views that have been materialized?

- When a fusion is materialized, any schema change to any of the child datasources will not be reflected in the materialized fusion. To resolve this the customer needs to edit the Fusion schema

### Is there any way to surface a dataset in a customer's instance that itemizes each fusion that has had manual performance tuning applied and whether the optimizations are working?

- Not at the moment
