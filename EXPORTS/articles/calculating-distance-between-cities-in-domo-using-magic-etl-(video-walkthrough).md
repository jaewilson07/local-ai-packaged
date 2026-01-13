---
title: "Calculating Distance Between Cities in Domo Using Magic ETL (Video walkthrough)"
url: /c/developerdomocom-community-edition/calculating-distance-between-cities-in-domo-using-magic-etl
author: Mark Snodgrass
published_date: Oct 27, 2022
updated_date: Nov 26, 2022 at 10:58 AM
tags: ['MajorDomo', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
likes: 2
---
# Calculating Distance Between Cities in Domo Using Magic ETL (Video walkthrough)
**Author:** Mark Snodgrass
**Published:** Oct 27, 2022
**Tags:** MajorDomo, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

If you have a group of people that are spread across the country and need to find the location that is the shortest distance for everyone, you can accomplish that using a built-in dataset in the Domo Dimensions Connector and the Distance function in Magic ETL.
The City Zips dataset in the Domo Dimensions Connector contains a list of cities with their zip codes and latitude and longitude. You can join this to other datasets that you have that contain zip codes or cities and states.
For example, I have a list of employees and their locations and I have a list of all major airports in the United States. I can join the City Zips dataset to each of those to add the latitude and longitude to that information and then join the two together. This allows me to calculate the distance between each person's location and every airports location using the distance function in the Formula tile.
Once created, I can then create visualizations to allow staff to choose various locations and employees to determine the optimal meeting location.
Watch this video to see how it is done.

﻿

﻿
