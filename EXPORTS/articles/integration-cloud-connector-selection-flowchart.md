---
title: "Integration Cloud || Connector Selection Flowchart"
url: /c/articles-and-knowledge-base/integration-cloud-connector-selection-flowchart
author: Jae Myong Wilson
published_date: May 17, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Articles &amp; Knowledge Base']
---
# Integration Cloud || Connector Selection Flowchart
**Author:** Jae Myong Wilson
**Published:** May 17, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMHdFREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--0f449a8e1e3f9c84122b0d23281485691ed979e2/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/4.png)

---

Andy Beier, VP of Domo [Integration Cloud](https://www.domo.com/integration-cloud) shares some hidden gems and under-utilized features in the Connector framework

My unofficial definition of **Integration Cloud **is all the stuff around getting data INTO and OUT of Domo Vault.  This spans but is not limited to:

- Connectors

- UPSERT & Writeback connectors

-
[ODBC ](https://knowledge.domo.com/Connect/Connecting_to_Data_Using_Other_Methods/Domo_ODBC_Data_Driver)for data egress

- Domo [Actions ](https://developer.domo.com/docs/domo-actions/start)framework

﻿

﻿

## Connector Options

When starting or mentoring clients on a new project I ( [https://www.onyxreporting.com](https://www.onyxreporting.com) ) usually recommend use this list for connecting data.

**Cloud Based**

- Standard library of connectors

- [Email connector](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/DataSet_via_Email_Connector)

-
[File Upload](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/File_Upload_Connector) connector

- JSON [No Code](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_IT/No-Code_JSON_Connector) (with [OAuth](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/JSON_No_Code_OAuth_Connector)) connector

- JSON [Adanced ](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/JSON_Advanced_Connector)connector

- SFTP [Push ](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/CSV_SFTP_Push_Connector)or [Pull ](https://knowledge.domo.com/Connect/Connecting_to_Data_with_Connectors/Configuring_Each_Connector/Connectors_for_File_Retrieval/CSV_SFTP_Pull_Connector)connector

**On Prem or local CSV file**

- [Workbench job](https://knowledge.domo.com/Connect/Connecting_to_Data_Using_Workbench_5/015Workbench_Capabilities_List)

- Java [Domo CLI](https://knowledge.domo.com/Administer/Other_Administrative_Tools/Command_Line_Interface_(CLI)_Tool#section_34)

- Python + [PyDomo](https://github.com/domoinc/domo-python-sdk)

**Considerations at each stage include**

- volume of data we're moving

- whether an incremental load strategy (APPEND or UPSERT) might be appropriate

- update schedule and data growth rate

If none of these options work, or you want ultimate control over your connector, you can build a [custom connector](https://developer.domo.com/docs/custom-connectors/connector-dev-studio).

[https://www.youtube.com/watch?v=OQLwYgU9smc&list=PLUy_qbtzH0S6-5oDbx3BsIv2Xk-JxJxWi&index=18](https://www.youtube.com/watch?v=OQLwYgU9smc&list=PLUy_qbtzH0S6-5oDbx3BsIv2Xk-JxJxWi&index=18)
