---
title: "TUTORIAL - Build a Custom Connector // Domo IDEA Exchange"
url: /c/builders-club/9wjx7
author: Jae Myong Wilson
published_date: May 14, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Get Help']
likes: 1
---
# TUTORIAL - Build a Custom Connector // Domo IDEA Exchange
**Author:** Jae Myong Wilson
**Published:** May 14, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Get Help

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMm9FREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--5f44373c38fc68ad93c6957ecae5d11f3d7e33d5/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/7.png)

---

﻿

﻿

Authentication Code

var res = httprequest.get('[https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson)');

DOMO.log('res: ' + res);

if(res.indexOf('FeatureCollection') > 0){
auth.authenticationSuccess();
}
else{
auth.authenticationFailed('Error connecting to [earthquake.usgs.gov](https://earthquake.usgs.gov)');
}
Reports

Past Hour
Past Day
Past 7 Days
Past 30 Days
Pull Data from last X day(s)

Process Data

DOMO.log("[metadata.report](https://metadata.report): " + [metadata.report](https://metadata.report));

if ([metadata.report](https://metadata.report) == "Past Hour") {
pastHour();
} else if ([metadata.report](https://metadata.report) == "Past Day") {
pastDay();
} else if ([metadata.report](https://metadata.report) == "Past 7 Days") {
past7Days();
} else if ([metadata.report](https://metadata.report) == "Past 30 Days") {
past30Days();
} else if ([metadata.report](https://metadata.report) == "Pull data from the last X day(s)") {
pastXDays();
} else {
DOMO.log([metadata.report](https://metadata.report) + " is not a supported report.");
datagrid.error(0, [metadata.report](https://metadata.report) + " is not a supported report.");
}

//functions

function pastHour() {
DOMO.log("pastHour");

processRecords(
"[https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson)"
);
}

function pastDay() {
DOMO.log("pastDay");

processRecords(
"[https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson)"
);
}

function past7Days() {
DOMO.log("past7Days");

processRecords(
"[https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson)"
);
}

function past30Days() {
DOMO.log("past30Days");

processRecords(
"[https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson)"
);
}

function pastXDays() {
DOMO.log("pastXDays");

processRecords(
"[https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=)" +
calculateEndDate() +
"&endtime=" +
currentDate()
);
}

function calculateEndDate() {
var now = new Date(); //This will be UTC when running server side
var end = new Date(now.getTime() - metadata.days * 1000 * 60 * 60 * 24);

DOMO.log("Start: " + now);
DOMO.log("End: " + end);

return (
end.getFullYear() +
"-" +
addOneLeadingZero(end.getMonth() + 1) +
"-" +
addOneLeadingZero(end.getDate())
);
}

function currentDate() {
var now = new Date(); //This will be UTC when running server side

return (
now.getFullYear() +
"-" +
addOneLeadingZero(now.getMonth() + 1) +
"-" +
addOneLeadingZero(now.getDate())
);
}

function processRecords(url) {
var res = httprequest.get(url);
DOMO.log("res" + res);

var data = JSON.parse(res).features;

datagrid.addColumn("Place", [datagrid.DATA](https://datagrid.DATA)_TYPE_STRING);
datagrid.addColumn("Magnitude", [datagrid.DATA](https://datagrid.DATA)_TYPE_STRING);
datagrid.addColumn("Time", [datagrid.DATA](https://datagrid.DATA)_TYPE_DATETIME); // date format needs to be yyyy-MM-dd'T'HH:mm:ss
datagrid.addColumn("URL", [datagrid.DATA](https://datagrid.DATA)_TYPE_STRING);

DOMO.log("data: ");

for (var i = 0; i < data.length; i++) {
var quakeDetails = data[i].properties;

datagrid.addCell([quakeDetails.place](https://quakeDetails.place));
datagrid.addCell(quakeDetails.mag);
datagrid.addCell(formatTime(quakeDetails.time));
datagrid.addCell(quakeDetails.url);

datagrid.endRow();
}
}

function formatTime(value) {
var d = new Date(value);

return (
d.getFullYear() +
"-" +
addOneLeadingZero(d.getMonth() + 1) +
"-" +
addOneLeadingZero(d.getDate()) +
"T" +
addOneLeadingZero(d.getHours()) +
":" +
addOneLeadingZero(d.getMinutes()) +
":" +
addOneLeadingZero(d.getSeconds())
);
}

function addOneLeadingZero(value) {
if (value < 10 && value > -10) {
value = "0" + value;
}

return value;
}
