---
title: "TUTORIAL -- Domo + K Means in MySQL // How to minimize distance traveled?"
url: /c/builders-club/domo-how-to-minimize-distance-travel-k-means-in-mysql
author: Jae Myong Wilson
published_date: Sep 9, 2021
updated_date: Jun 20, 2022 at 05:42 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
---
# TUTORIAL -- Domo + K Means in MySQL // How to minimize distance traveled?
**Author:** Jae Myong Wilson
**Published:** Sep 9, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

---

**Use Case
**I have five ambulances, what is the best way to distribute them around the city to minimize distance traveled?
﻿

﻿

## Code Samples

### Calculate the distance between two points

Note the use of the least() function.

-- [https://stackoverflow.com/questions/24370975/find-distance-between-two-points-using-latitude-and-longitude-in-mysql](https://stackoverflow.com/questions/24370975/find-distance-between-two-points-using-latitude-and-longitude-in-mysql)

SELECT
c.`id` as `cluster_id`,
d.`id` as `location_id`,

111.111 *
DEGREES(ACOS(LEAST(1.0, COS(RADIANS(`lat`))
* COS(RADIANS(`c_lat`))
* COS(RADIANS(`lng` - `c_lng`))
+ SIN(RADIANS(`lat`))
* SIN(RADIANS(`c_lat`))))) AS distance_in_km,
`c_lat`,
`lat`,
`c_lng`,
`lng`
FROM
`km_data` d
, `test_clusters`  c
order by d.`id`, c.`id`
### K-means implementation

- Seed a table with a user-defined number of clusters.

- Assign datapoints to the nearest cluster (ORDER BY `distance` LIMIT 1)

- Recalculate each cluster centroid (AVG)

- LOOP over steeps 2 and 3 until cluster allocation stops shifting (note, in the code provided, we loop 1000 times)

-- [https://jonisalonen.com/2012/k-means-clustering-in-mysql/](https://jonisalonen.com/2012/k-means-clustering-in-mysql/)

CREATE PROCEDURE kmeans(v_K int)
BEGIN

DECLARE counter INT default 1 ;

-- initialize clusers
TRUNCATE km_clusters;
INSERT INTO km_clusters (c_lat, c_lng) SELECT lat, lng FROM km_data LIMIT v_K;

REPEAT
-- assign clusters to data points
UPDATE `km_data` d SET `cluster_id` = (SELECT `id` FROM `km_clusters` c
ORDER BY
-- POW(d.`lat`-c.`lat`,2)+POW(d.`lng`-c.`lng`,2)

DEGREES(ACOS(LEAST(1.0, COS(RADIANS(`lat`))
* COS(RADIANS(`c_lat`))
* COS(RADIANS(`lng` - `c_lng`))
+ SIN(RADIANS(`lat`))
* SIN(RADIANS(`c_lat`))))) -- distance in KM

ASC LIMIT 1);

-- calculate new cluster centroid
UPDATE `km_clusters` C, (SELECT `cluster_id`,
AVG(`lat`) AS `lat`, AVG(`lng`) AS lng
FROM `km_data` GROUP BY `cluster_id`) D
SET
C.c_lat=D.lat, C.c_lng=D.`lng`,
C.`counter` = `counter`

WHERE C.`id`=D.`cluster_id`;

-- UNTIL ROW_COUNT() = 0 END REPEAT;
SET counter = counter + 1;

UNTIL counter >= 1000 END REPEAT;

END

In Domo the Data can be visualized using the standard lat/long map or the lat/long route map
﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBL09hRlE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--428a1ac561a23b0d8138eb81cc701c4a572127df/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/image.png)
﻿

### Articles referenced:

[https://www.edureka.co/blog/k-means-clustering/](https://www.edureka.co/blog/k-means-clustering/)
[https://jonisalonen.com/2012/k-means-clustering-in-mysql/](https://jonisalonen.com/2012/k-means-clustering-in-mysql/)
[https://stackoverflow.com/questions/24370975/find-distance-between-two-points-using-latitude-and-longitude-in-mysql](https://stackoverflow.com/questions/24370975/find-distance-between-two-points-using-latitude-and-longitude-in-mysql)
[https://www.nhc.noaa.gov/gccalc.shtml](https://www.nhc.noaa.gov/gccalc.shtml)
