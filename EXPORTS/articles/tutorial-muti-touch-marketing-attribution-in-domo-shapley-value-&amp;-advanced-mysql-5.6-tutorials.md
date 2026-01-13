---
title: "TUTORIAL:  Muti-Touch Marketing Attribution in Domo // Shapley Value &amp; Advanced MySQL 5.6 tutorials"
url: /c/builders-club/tutorial-muti-touch-marketing-attribution-in-domo-shapley-value-advanced-mysql-5-6-tutorials
author: Jae Myong Wilson
published_date: Sep 21, 2021
updated_date: Jun 20, 2022 at 05:43 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# TUTORIAL:  Muti-Touch Marketing Attribution in Domo // Shapley Value &amp; Advanced MySQL 5.6 tutorials
**Author:** Jae Myong Wilson
**Published:** Sep 21, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeC9FRmc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--d10e8c46c1c650e238c18f650d2e0f6a0c03b853/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Luma%20(12).png)

---

## Set the Stage:  What is Marketing Attribution?

In marketing, attribution seeks to answer "who gets credit for converting a prospect into a sale?"

Given that modern marketing frequently uses a variety of channels to advertise to customers (Facebook, Instagram, Paid Search etc.), a team with a finite budget may seek to understand which channels are the most effective at converting customers.

Unfortunately, customer interactions with your ads are seldom mono channel.  We've all had the experience of starting with an organic search for a pair of shoes, we click a link that takes us to your website and suddenly ads appear in Facebook, Instagram as well as the websites we frequent.

When I finally convert (make a purchase), which channel should get credit?
﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMTdFRmc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--41664b0a81bc2c439273d3bbed1a43df524837c9/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/1_ftV8NIEJu_AcHERYLsJZFg.png)
﻿[https://medium.com/analytics-vidhya/the-shapley-value-approach-to-multi-touch-attribution-marketing-model-e345b35f3359](https://medium.com/analytics-vidhya/the-shapley-value-approach-to-multi-touch-attribution-marketing-model-e345b35f3359)

There are a handful of commonly accepted methods for attributing credit.  **Last Click **or **First Click **has a 'winner-takes-all' approach and assigns all credit to the first or last channel.  **Linear **distributes credit across all channels that participated in the journey, while **Time Decay **assumes that more recent interactions had a greater impact on conversion.

> If you're using Salesforce, you probably are using Last Touch attribution!

If you have a 'Reason Code' or 'Lead Source' on your Opportunities, you're probably recording the last activity or interaction with the account which lead to a status change.  In other words, you're assuming that the Last Touch was 100% responsible for the change.

To get a more nuanced understanding, instead of a **Single-Touch **attribution model, we might consider distributing credit for the conversion across multiple channels that participated in the customer journey.

## Marketing Attribution and Game Theory

Consider team-based e-sport League of Legends, where a team of 5 players competes against another team of 5. Each individual will contributes to the binary outcome (win / loss), but in a pick-up game, you'll frequently have 2 great players, two average players, and one teammate who's so bad or toxic they're a detractor to the team.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBLzNFRmc9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--f2349e931b38e7383d24bd995c0213f8827ebec1/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/riot-8.jpg)
﻿
The same game theory can be applied to marketing attribution.  If each customer journey is evaluated as a coalition of individual contributions from each member channel, we can use the **Shapley Value **to assess which channels have the most positive *and negative *impact on the coalitions they're a part of.

### **Articles Referenced**

[https://clearcode.cc/blog/game-theory-attribution/](https://clearcode.cc/blog/game-theory-attribution/)
[https://towardsdatascience.com/data-driven-marketing-attribution-1a28d2e613a0](https://towardsdatascience.com/data-driven-marketing-attribution-1a28d2e613a0)

### Download Dataset:

[https://www.kaggle.com/hughhuyton/multitouch-attribution-modelling#Data](https://www.kaggle.com/hughhuyton/multitouch-attribution-modelling#Data)

## Introduction﻿

﻿

## 1_Establishing Customer Journey using Window Functions in MySQL 5.6

The first step is to construct the Customer Journey, i.e. "for any given interaction, which channels have you previously interacted with?"

In the tutorial, we'll construct 3 permutations of the journey,

- the actual journey - AABCDDA

- the journey represented as channel changes - ABCDA

- the journey with distinct channels - ABCD

To construct the journey, we'll need to use Window Functions to view all the rows that belong to a user before the current_row.
﻿

﻿

Domo's MySQL Dataflow engine uses MySQL v 5.6 which does not include the ability to leverage window functions

[https://www.mysqltutorial.org/mysql-window-functions/](https://www.mysqltutorial.org/mysql-window-functions/)

So instead we use variables to pass values from row to row.
﻿

[

](#remove-attachment)

[

![](https://cdn.sstatic.net/Sites/stackoverflow/Img/apple-touch-icon@2.png?v=73d79a89bded)

ROW_NUMBER() in MySQL

Is there a nice way in MySQL to replicate the SQL Server function ROW_NUMBER()?

For example:

SELECT
col1, col2,
ROW_NUMBER() OVER (PARTITION BY col1, col2 ORDER BY col3 DESC) AS intRow
...

https://stackoverflow.com/questions/1895110/row-number-in-mysql

](https://stackoverflow.com/questions/1895110/row-number-in-mysql)

﻿

## 2_Convert Ordered Series into Sets

The customer journey is an ordered series (i.e. first this happened, then that happened).  We can already calculate how many conversions each distinct journey is responsible for; however, we need to calculate how many conversions each coalition (team composition) is responsible for.

In cooperative game theory, we assume that each coalition will perform the same regardless of which order the players play; therefore, a coalition isn't thought of as a sequence of player plays (customer journey) rather an unordered set.

Customer journey A > B > C and journey B > C> A have the same coalition, channels [A,B,C]

In MySQL, we'll convert customer journeys into coalitions by rearranging the channel members into alphabetical order.  Then we'll sum conversions by the newly defined coalition.
﻿

﻿

##

## **3_Define all the possible play orders per coalition**

We already assume that each coalition (combination of channels) will consistently score the same number of points, but we also know that depending on the order each play plays in, a player may contribute a different number of points.

We curently we have a list of all the coalitions.  For each coalition, we need to identify all the possible orders the teammates can play.

Assume

- coalition AB always scores 10 points.

- given two players, there are two play orders A > B and B > A

- player A on their own  always scores 7 points

- player B on their own always scores 5 points

Game A > B
Player A scores 7 points, coalition AB is worth 10 points, therefore player B must have contributed 3 points.

Game B > A
Player B scores 5 points, coalition AB is worth 10 points, therefore player A must have contributed 5 points.

Player A's average contribution is ( 7 + 5 ) / 2 = 6
Player B's average contribution is ( 3 + 5 ) / 2 = 4

## 3_Calculate all the Play Combinations

## **﻿

﻿**

## 4_Generate a row to calculate each player's marginal contribution in a game.

**﻿

﻿****

**

## 5_Calculate each Player's marginal Contribution

To calculate each player's marginal contribution at their turn in the game, we must think of each stage of the game as it's own coalition (unordered set of players) and look up how much that coalition scores.

Assume

- coalition ABC always scores 13 points.

- coalition AB always scores 9 points.

- given three players, there are 6 play orders ABC, ACB, BAC, BCA, CAB, CBA

- player A on their own always scores 7 points

- player B on their own always scores 5 points

- player C on their own always scores 3 points.

NOTE:  We are looking up coalition values based on the first transform where we calculate sum(Conversions) GROUP BY customer_journey_ordered

In game A > B > C
Coalition [empty ] is worth 0 points
Coalition [A] is worth 7 points.  therefore at stage A, player A adds 7 - 0 = 7 points
Coalition [AB] is worth 9 points, therefore at stage A > B, player B adds 9 - 7 = 2 points
Coalition [ABC] is worth 13 points, therefore at stage A > B > C player C adds 13 - 9 = 4 points

We now must calculate marginal contributions for each of the other play orders and then calculate marginal contribution.
﻿

﻿
