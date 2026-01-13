---
title: "Hashing and Encrypting Data in Domo / Columnar PDP [as of 5/5/2022]"
url: /c/developerdomocom-community-edition/hashing-and-encrypting-data-in-domo-columnar-pdp-as-of-5-5-2022
author: Jae Myong Wilson
published_date: May 13, 2022
updated_date: Nov 26, 2022 at 10:59 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# Hashing and Encrypting Data in Domo / Columnar PDP [as of 5/5/2022]
**Author:** Jae Myong Wilson
**Published:** May 13, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Based on encryption as described here:
[https://domohelp.domo.com/hc/en-us/articles/360043437413-Encrypting-Decrypting-and-Hashing-Workbench-5-Data](https://domohelp.domo.com/hc/en-us/articles/360043437413-Encrypting-Decrypting-and-Hashing-Workbench-5-Data)

## Use Case:

Encrypt a column to hide the actual value from users, but still be able to use the column to define PDP policies or part of a COUNT(DISTINCT) calcs.

Ideally, be allow specified users to decrypt encrypted columns without using Workbench.

Question:  Would the PDP functionality be able to apply PDP on the unencrypted value or would the pdp be assigned on the hashed value.

## "Working as Designed"

Support 10/5/22 - You can only decrypt columns in Sumo tables that have been pushed via Workbench.

Any PDP policies applied would be based on the encrypted values.

## Bug Report

Via the Set_Schema command in the Domo / Jave CLI it is possible to alter the schema of a dataset, but when you reupload the dataset using workbench (with encryption) the dataset does not behave as expected in Domo (it is impossible to unencrypt the data in sumo tables).

Steps Taken:

-  we uploaded the dataset with encryption enabled

- We removed the encryption settings via set_schema in the CLI
As expected the column remains encrypted in Domo but we cannot decrypt it using Sumo Tables.

- We set the schema to the original configuration using the CLI
We still cannot decrypt the column in Sumo tables

- We reran the workbench job (with same encryption transforms)
We still cannot decrypt the column in Sumo Tables.
