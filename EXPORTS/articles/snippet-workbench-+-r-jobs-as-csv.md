---
title: "SNIPPET - Workbench + R - Jobs as CSV"
url: /c/developerdomocom-community-edition/workbench-jobs-to-csv-r-snippet
author: Jae Myong Wilson
published_date: Jun 10, 2021
updated_date: Oct 11, 2021 at 09:38 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# SNIPPET - Workbench + R - Jobs as CSV
**Author:** Jae Myong Wilson
**Published:** Jun 10, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Courtesy of Jimmy

pacman::p_load(tidyverse, lubridate, glue, fs, janitor, magrittr, DomoR, domorrr, clipr, fst, jsonlite, readxl)
this_folder <- "path_to_folder_for_workbench_json_files"
dir_ls(this_folder) %>% fs::file_delete()
# command line epxport my workbench jobs
system('"c://program files/domo/workbench/wb" export-jobs --outputfolder path_to_folder_for_workbench_json_files --server [yourdomo.domo.com](https://yourdomo.domo.com) --force True')
# returns [1] 0 when runs successfully
(these_files <- dir_ls(this_folder)
these_files %>%
head() %>%
map_dfr(function(this_file) {
x <- this_file %>%
read_file() %>%
fromJSON(flatten = TRUE)
tibble(
workbench_job_name = x$name,
domo_dataset = x$DataSource$Name,
last_sucessful_run = anytime::anytime(x$lastSuccessfulRun / 1000),
input_filename = x$WorkbenchConfig$DataProvider$Properties$FileName %>%
str_remove_all(., ".*\\\\"),
input_filepath = x$WorkbenchConfig$DataProvider$Properties$FileName %>%
str_extract(., ".*\\\\"),
input_file = x$WorkbenchConfig$DataProvider$Properties$FileName
)
}) %>%
mutate_at(vars(matches("filepath|input_file")), list(~ str_replace_all(., fixed("\\"), "/")))
