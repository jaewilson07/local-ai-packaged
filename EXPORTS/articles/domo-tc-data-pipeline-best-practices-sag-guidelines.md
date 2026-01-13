---
title: "Domo TC // Data Pipeline Best Practices // SAG Guidelines"
url: /c/articles-and-knowledge-base/domo-tc-data-pipeline-best-practices-sag-guidelines
author: Jae Myong Wilson
published_date: May 17, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
comments: 1
---
# Domo TC // Data Pipeline Best Practices // SAG Guidelines
**Author:** Jae Myong Wilson
**Published:** May 17, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBenNFREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--e45d10f712cb7a655167cd9e7b9e8cc8bdc80873/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/4.png)

---

## SAG **Charter**

The SAG aims to drive strategies that appropriately leverage each component of Domo’s architecture to help solve the unique business problems facing Domo’s customers.

# Architecture Features

This information is crucial for planning the data pipeline.

- Key Data Source Systems

- Domo Features to be used (Cloud Connectors, Domo Workbench, Other API, Java CLI, Magic ETL, Data Stacker, Data Assembler, Partition, Upsert).

- Estimated total size of data / growth rate month-on-month.

- Estimated largest dataset.

- Frequency of updates

## What is a Robust Pipeline?

A robust pipeline is the opposite of a fragile one. A robust pipeline will tolerate
errors/outages and will self-heal when the outage has been resolved. A fragile pipeline may result in a corrupt dataset when an error or outage occurs. If a fragile data pipeline accidentally runs an extra time, it will often end up with duplicate data (and therefore a corrupt dataset).

## What are the attributes of an Efficient Pipeline?

An efficient pipeline is designed to minimize data movement and only materializes the required data.  An efficient pipeline leverages smart design to only operate on changed and/or new data. An inefficient pipeline endlessly re-processes the same
data over and over again. An efficient pipeline minimizes Domo’s costs to process AND MORE IMPORTANTLY improves customer satisfaction.

***You should be able to answer “TRUE” to all of these statements.
***

- If one of the source systems is down during pipeline execution, the data be able to recover with no duplication and minimal manual intervention.

- There are no manual processes that need to be employed periodically to keep my pipeline healthy.

- Data will not be corrupted if the pipeline is accidentally run twice for the same period.

- Metrics are streamlined to minimize duplication and overlap across multiple data pipelines. There is minimal risk that a customer MIGHT create two cards, one from each data pipeline, and see conflicting values due to timing/logic of each data pipeline.

- The pipeline execution time does not grow linearly as history accrues. For example, a pipeline should not reprocess the entire history along with the new data (recursive dataflows).

- The pipeline minimizes un-needed materialization of metrics especially for things that need to be calculated at run time such as ratios or rates. This ensures filter operations by cards/pages will not be in conflict with materialized/calculated metrics.

- The pipeline is appropriate for the business requirements for data latency and the amount of data. Many “row-at-a-time” approaches to data ingestion and transformation will not meet the business requirements IF data volume is high and data latency decreases.

- The pipeline has a maintenance and support plan in place to handle issues when they arise.

- The pipeline includes monitoring to ensure issues are discovered and addressed as quickly as possible.
