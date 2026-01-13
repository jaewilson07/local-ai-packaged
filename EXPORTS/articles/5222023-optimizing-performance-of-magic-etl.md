---
title: "5/22/2023 - Optimizing Performance of Magic ETL"
url: https://datacrew.circle.so/c/articles-and-knowledge-base/5-22-2023-unblack-boxing-magic-etl
author: Jae Myong Wilson
author_tags: ['Admin', 'Freelancer', 'Domo Sensei']
space: Articles &amp; Knowledge Base
published_date: May 22, 2023
updated: May 22, 2023 at 12:03 PM
likes: 0
comments: 0
---

# 5/22/2023 - Optimizing Performance of Magic ETL

**Author:** Jae Myong Wilson
**Credentials:** DataCrew Community Admin // Data Whisperer
**Tags:** Admin, Freelancer, Domo Sensei
**Space:** Articles &amp; Knowledge Base
**Published:** May 22, 2023
**Likes:** 0 | **Comments:** 0

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBCSTk0QXdFPSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--848dc20d725d86d15556a8fef6694e3d56dd1d69/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image%20(4).png)

---

Highlights from a Slack Conversation about optimizing a Magic ETL dataflow.
[https://domousergroup.slack.com/archives/C013AKYGP5W/p1684359904358029](https://domousergroup.slack.com/archives/C013AKYGP5W/p1684359904358029)

**Question:**
Is there's a noticeable difference between a dataflow running through tiles or formulas? For example is it quicker to use a replace text tile rather than a replace formula.

**@jaeW_at_Onyx:**
Haha. Yes and no.
So they both get translated into Java (I believe).  So that's going to be very similar performance.  What may differ is if you write a series of formula getting translated to Java it cannot be guaranteed that it will be the same as using a very controlled set of tiles with limited parameters.

If you asked "is REGEX going to be faster than a CASE" statement, I would guess "not materially"
You probably do worse damage with your JOIN or GROUP BY tile.

**@Tim_Ehat**
A few general notes from me on this thread. I can’t be super specific, but Jae is on the right track. Magic actions are going to execute in a Java VM. Splitting on a separator using the ETL tile may be faster than an Add Formula tile using a regex. But that’s less about “special tile” vs “function tile” and more about “regex” vs “substring” performance. Several of our tiles are really just powered by the formula tile under the hood.

**Question**
Is there a significant performance difference between changing data types on the input dataset versus formula tile or alter tile?

**@Tim_Ehat**
With respect to overriding data types on the input using data handling: When your input dataset exists in Vault, we load the raw data for it from there. In the case of API datasets and connectors (and maybe workbench… depends on the version, I think), the data in Vault is in CSV. Sometimes data uploaded to Vault doesn’t match the dataset schema. This “data handling” option is a good way to instruct Magic to ignore the schema and use something else. That means parsing that raw CSV as that new data type.
That compares to using another action after the input to change data type (formula/set column type/alter schema… they should all perform the same, I think). In that case, the data type is a conversion of one already parsed value to another type.
This might some golden-path CSV parsing code may get bypassed if you override the data type on the input tile.

If you see a perf difference when reading data from the output of another magic dataflow when using the input tile overrides vs another tile, [that's not expected behavior].

**Question:**
Why do JOINS, GROUP BY and RANK function slow my Magic ETL dataflow?

**@jaeW_at_Onyx:**
JOINS and GROUP BYs and RANK tiles can be thought of as blocking functions where  you cannot move to the next step until all the data is loaded.
This is not 100% accurate but if you think of it this way you'll understand why your performance is so poor.
I cannot GROUP BY and SUM (and move onto the next step) until all my data has arrived at that tile).  I also cannot really distribute the work across multiple computers because in order to know the SUM i must have all the rows applicable to that tile (same for RANKING).
consider a formula tile with a CASE statement.  That's not a blocking function because all the information i need to calculate the CASE statement exists within that one row of data.  I don't have to wait for all my data to arrive before i can begin processing.  in fact.  if i needed to apply CASE statements to 100000 rows of data, I could split that task between 10 computers (distributed processing) because each row of data has all the information necessary for calculating the CASE statement.

TLDR:  go back and count the number of blocking functions in your ETL (JOIN, GROUP_BY, RANK).  THAT's why it takes so long.

Also, keep in mind your data is not running in a database.  so there is no indexing beforehand to improve performance by structuring your data into tables.  Instead, think of your data as streams of text or batches of CSV files.

**@Tim_Ehat:**
As far as indexing goes, Magic basically automatically indexes your data. but where a database will do that as the rows come in... Magic is getting all the rows for the “first” time when the job runs. When doing a join, if one side of the join fits in memory, you’re pretty golden.. the other side can stream through. I can’t really say exactly how much memory we allocate to flows, (we’re always tweaking things trying to make it better). if you ever see a flow with growing row sizes and performance suddenly drops off a cliff, it may be that you hit a threshold where we needed to start buffering things to disk. we’ve eliminated a fair amount of that over the last year or so.

Additionally if you think about how Pandas works -- your entire dataset has to fit in memory in order to efficiently execute the JOIN.  I don't know how much memory Domo allocates to Magic, but if the entire dataset has to fit in memory, the larger the dataset the larger the chance Domo has to use a page file to offload some of your data to disk as it's processing it.

TLDR:  Magic ETL is NOT executing in a database engine, so think about how your computer would handle processing large bodies of text, and it might make it a little clearer why you're taking performance hits

**@Tim_Ehat:**
What Jae says about blocking actions is right. I’d love for us to give you the “graph” view of the dataflow on an execution details page for Magic dataflows, coloring tiles in a heatmap sort of way to help you see where processing time was spent (and also maybe find a way to call out blocking actions). Would love that feedback to come in via more channels.

**QUESTION:  great, so how do i make it better?

@jaeW_at_Onyxr**
1. Do stuff in a database layer that databases are exceptionally good at.  I.e. where possible shift some of your processing into Adrenaline Dataflows or Dataset Views (specifically the JOINS and GROUP BYs).  Where possible AVOID JOINS and GROUP BYs in Magic.  it might be 'cheaper' to just write 10M rows to disk instead of premature aggregation.

2. take some of your stages of ETL and move them into separate dataflows.  if the first half of your dataflow is about claculating 'the right metric' and the second half of your dataflow is about structuring your data for presentation in a dashboard, i don't need to recalculate 'the right metric' every time i tweak my dashboard presentation.  so separate them into two flows.

3.  Note( I can already hear @bvk  complaining that some people have row limits.  Fine.  Do your ETL development in smaller chunks against _DEV datsets, then unify the data pipeline into one master dataflow to save on row_count.

**On JOIN optimization in Magic**
**@jaeW_at_Onyx:
**it used to be best practices to put the smaller table on the left to prevent a 10,000 row duplicates error (back in 2018 / Magic 1.  This is no longer the case)

**@Tim_Ehat:
**The engine should be loading both sides simultaneously until one side is done and then streams through the other side. shouldn’t matter left or right on that

**@Alexis Lorenz:
**It's not a thing anymore, Tim - not an error we get anymore.

**@Tim_Ehat:
**ah, yeah, the ol’ 10k duplicates issue. that was a Magic 1 thing. (we hated it, too!)

Want answers to your questions in realtime?
Join our 🧵 Domo User Group Slack -- [https://domousergroup.carrd.co/](https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqbmRtcG90OElMekhRNjdER1VGME15QjQ0SmV4d3xBQ3Jtc0tsOUVRdmJlOVA3cnJuUk1xRHVZQ2JJU1dPUVZTbUNwTHhMRVZGSzV1RjJ1NUZMNHhnQ1JDNzNJc2hhSUZoaENWUmFNWUt4TFg3el9DWDUzazBPR2lMeTIydE5UY2NPWm1mcWxiZ3Z2RmJrMmppeGxtYw&q=https%3A%2F%2Fdomousergroup.carrd.co%2F&v=cbpCxXoenKU)
