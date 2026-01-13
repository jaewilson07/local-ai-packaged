---
title: "Data Lake Security &amp; Best Practices"
url: /c/articles-and-knowledge-base/data-lake-security-best-practices
author: Jae Myong Wilson
published_date: Jun 1, 2021
updated_date: Jun 20, 2022 at 05:29 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# Data Lake Security &amp; Best Practices
**Author:** Jae Myong Wilson
**Published:** Jun 1, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBL1VyRFE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--9a8f23ddf5e77d3907fe707f27dcbe1a5a349efd/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/pexels-igor-starkov-776516.jpg)

---

## Lock down the Data Layer

Follow the least-permissions-required approach.  Domo does not support schemas for separating layers of the data mart UI.  Carefully consider which layers you give access to.  Secure using PDP and report using Data Governance Connectors

- KB:  [Managing User Accounts for Connectors](https://domohelp.domo.com/hc/en-us/articles/360042926054-Managing-User-Accounts-for-Connectors#:~:text=To%20share%20an%20account%20with%20another%20user%2C&text=Click%20and%20select%20Share%20account,to%20share%20the%20account%20with.)

- KB: Domo [PDP](https://domohelp.domo.com/hc/en-us/sections/360007334593-Personalized-Data-Permissions-PDP-)

-
**Design your semantic layer around secure zones: **Identity who needs access to what assets. For example, administrators and data engineers will need access to physical data sources, while access to virtual datasets and curated data will be sufficient for analysts and data scientists.

-
**Apply column- and row-level permissions in the semantic layer: **By doing this, you eliminate complexity by not having to make changes at the application level or create multiple protected versions of the same dataset. Data consumers simply receive the data they need with implemented security that will allow them to see just what they need.

-
**Apply permissions based on the capabilities of the service**: Cloud vendors such as AWS and Azure provide a variety of mechanisms, including IAM policies, role-based access, encryption at rest and transit, and key management, just to name a few.

-
**Secure and govern user access**: This will always ensure that the enterprise’s data is not open to the public. It also provides the opportunity to identify who can access the data, as well as what actions they can take.

-
**Secure and govern users’ rights**: This allows companies to control what privileges an authenticated entity can have within the system. It is imperative to have a security plan laid out before the data lake is created, as this will provide an opportunity to define roles and privileges.

-
**Leverage metadata governance: **Securing your data is only part of the story—securing metadata is just as important. Armed with metadata, an attacker can target users as well as applications within your organization and gain access to data. Metadata controlling systems such as AWS’s Glue can help alleviate that issue through IAM-based policies. Similarly, Azure Data Catalog allows you to specify who can access the data catalog and what operations they can perform.

Reposted from "Big Data Quarterly."  [Securing Your Cloud DataLake with an in depth Defense Approach](https://www.dbta.com/BigDataQuarterly/Articles/Securing-Your-Cloud-Data-Lake-With-an-In-Depth-Defense-Approach-141403.aspx) original author: [Jacques Nadeau](https://www.dbta.com/Authors/Jacques-Nadeau-7681.aspx)
