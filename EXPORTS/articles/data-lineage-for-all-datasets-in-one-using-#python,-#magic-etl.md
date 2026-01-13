---
title: "Data lineage for all datasets in one using #Python, #Magic ETL"
url: /c/articles-and-knowledge-base/data-lineage-for-all-datasets-in-one-using-python-magic-etl
author: Oleksii
published_date: Nov 8, 2022
updated_date: Nov 08, 2022 at 03:30 AM
categories: ['Articles &amp; Knowledge Base']
likes: 2
---
# Data lineage for all datasets in one using #Python, #Magic ETL
**Author:** Oleksii
**Published:** Nov 8, 2022
**Categories:** Articles &amp; Knowledge Base

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNyt2Znc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d08af4a407dea51370beef0f9eed7724faaaf442/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/bxwqx)

---

Data Governance with Domo is one of the key points of Data platform lifecycle.
I would like to share with you this video. It explains how to build the ETL flow based on Domo Governance connectors and produce data lineage for all datasets in your instance.
That data lineage can be used for Project health monitoring, identify which connector/dataset may impact your final data table.
﻿

﻿And here is the code presented in the video

# Import the domomagic package into the script
from domomagic import *
import pandas as pd

# read data from inputs into a data frame
df_input = read_dataframe('Datasets')
df_dataflow_details = read_dataframe('Dataflow details')

def append_row(df, row):
return pd.concat([
df,
pd.DataFrame([row], columns=row.index)]
).reset_index(drop=True)

df_result = pd.DataFrame(columns=('Leaf_Dataset_ID','Output_Dataset_ID', 'Parent_Dataflow_ID', 'Input_Dataset_IDs'))

def get_lineage (leaf_dataset, dataset, df):

dataflow_id=None
global df_result

if df[(df['Output Dataset ID'] == dataset)].shape[0] >0:
dataflow_id = df[(df['Output Dataset ID'] == dataset)]['Dataflow ID'].values[0]
#get inputs for the dataflow id
df_inputs =df[(df['Dataflow ID'] == dataflow_id)&(df['Input Dataset ID'].notnull())]
#input from column to string separated by commas
str_inputs = ','.join(df_inputs['Input Dataset ID'])

new_row = pd.Series({'Leaf_Dataset_ID':leaf_dataset,
'Output_Dataset_ID':dataset,
'Parent_Dataflow_ID':dataflow_id,
'Input_Dataset_IDs':str_inputs})
#add the row to result dataframe
df_result = append_row(df_result, new_row)

if dataflow_id is None:
return;
for index, row in df_inputs.iterrows():
#to avoid recursive flow and infinite loop
if dataset not in row['Input Dataset ID']:
get_lineage(leaf_dataset, row['Input Dataset ID'],df)
return

for index, row in df_input.iterrows():
get_lineage(row['Dataset ID'], row['Dataset ID'], df_dataflow_details)

df_result=df_result.drop_duplicates(keep='first').reset_index(drop=True)

# write a data frame so it's available to the next action
write_dataframe(df_result)

[#ISolvedItWithDomo](https://www.youtube.com/hashtag/isolveditwithdomo)
[#Domo](https://www.youtube.com/hashtag/domo)
[#DomoCommunity](https://www.youtube.com/hashtag/domocommunity)
[#BISensei](https://www.youtube.com/hashtag/bisensei)

Watch this and other videos on my Youtube channel [@BISensei](https://www.youtube.com/@bisensei)
