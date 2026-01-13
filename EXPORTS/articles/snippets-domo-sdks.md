---
title: "SNIPPETS - Domo SDKs"
url: /c/developerdomocom-community-edition/domo-sdks-code-snippets
author: Jae Myong Wilson
published_date: May 14, 2021
updated_date: Jun 20, 2022 at 05:27 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# SNIPPETS - Domo SDKs
**Author:** Jae Myong Wilson
**Published:** May 14, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBMkVFREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--fc2c78bd47a3b8937ee731592563d22c0d915bf0/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/8.png)

---

### Export CardData

public static void ExportCardData(String accessToken, String domain, Long cardID, String fileName) {

DomoClient client = new DomoClient(new DomoApiTokenAuth(accessToken), domain);
ResourceManager resourceManager = new ResourceManager(client);

CardExportRequest exportRequest = new CardExportRequest();

try {

resourceManager.exportCardData(cardID, exportRequest, new File(fileName));

}
catch (Exception e) {
System.out.println(e.getMessage());
}
}

### Export CardDataWithWeekFilter

public static void ExportCardDataWithWeekFilter(String accessToken, String domain, Long cardID) {

DomoClient client = new DomoClient(new DomoApiTokenAuth(accessToken), domain);
ResourceManager resourceManager = new ResourceManager(client);

CardExportRequest exportRequest = new CardExportRequest();
exportRequest.setDateTimeElement("WEEK");

try {

resourceManager.exportCardData(cardID, exportRequest, new File(fileName));

}
catch (Exception e) {
System.out.println(e.getMessage());
}
}

### Query Data

private static void queryData(String accessToken, String domain, String datasetID) {
// Authenticate
DomoClient domoClient = new DomoClient(new DomoApiTokenAuth(accessToken), domain);

// Setup a data manager
DatasetManager dataManager = new DatasetManager(domoClient);

try {
// Setup the schema to query
Schema s = dataManager.getSchema(datasetID);

DataQueryBuilder queryBuilder = new DataQueryBuilder();
for (Schema.Column col : s.getColumns()) {
queryBuilder.addColumn(col.getName());
}

// Setup the query
queryBuilder.addWhereEquals("Priority", "4");

// Request the first 25 rows of data
DataQueryRequest request = queryBuilder.getDataQueryRequest();
LimitClause limit = new LimitClause(25, 0);
request.setLimitClause(limit);

DataQueryResponse response = dataManager.queryDataSet(datasetID, request);

// Processs the response
List<List<Object>> data = response.getRows();
System.out.println("Query 'WHERE `Priority` = 4' returned " + data.size() + " rows.");

// Convert to a JSon return object
JSONArray jsonArray = new JSONArray();
for (List<Object> list : data) {
JSONArray newArray = new JSONArray(list);
jsonArray.put(newArray);
}

for (int i = 0; i < jsonArray.length(); i++) {
System.out.println(jsonArray.get(i).toString());
}

// Setup the schema to query
queryBuilder = new DataQueryBuilder();
for (Schema.Column col : s.getColumns()) {
queryBuilder.addColumn(col.getName());
}

// Setup the query
queryBuilder.addWhereLike("Configuration Item", "TSV%");

// Request the first 25 rows of data
request = queryBuilder.getDataQueryRequest();
limit = new LimitClause(25, 0);
request.setLimitClause(limit);

// Processs the response
response = dataManager.queryDataSet(datasetID, request);
data = response.getRows();

System.out.println("");
System.out.println("Query 'WHERE `Configuration Item` LIKE TSV%' returned " + data.size() + " rows.");

jsonArray = new JSONArray();
for (List<Object> list : data) {
JSONArray newArray = new JSONArray(list);
jsonArray.put(newArray);
}

for (int i = 0; i < jsonArray.length(); i++) {
System.out.println(jsonArray.get(i).toString());
}
}
catch(RequestFailedException | JSONException ex) {
System.out.println(ex.getMessage());
}
}

### Create Net New Users based off a CSV Input

// Create net new users based off a CSV input file. The utility walks the CSV line for line looking to see if the
// user is in Domo or not. If it is, move to the next line, if it is not create new 'participant' user. The utility
// expects a Header row, with firstName, lastName, eMail. The name of the columns does not matter. It looks at them
// by ordinal
//
// Usage:
// java -jar createUsers.jar <AccessToken> <Domain> <FilePath>
//
// arg0 - token
// arg1 - domain
// arg2 - file path
public static void createUsers(String[] args) throws RequestFailedException {

if (!args[1].contains("[domo.com](https://domo.com)")) {

System.out.println("Domain parameter not a valid Domo domain: " + args[1]);
return;

}

IDomoAuth authentication = new DomoApiTokenAuth(args[0]);
DomoClient client = new DomoClient(authentication, args[1]);

UsersManager usersManager = new UsersManager(client);

FileWriter logWriter = null;

try {

logWriter = new FileWriter(System.getProperty("user.dir") + "/CreateUsers.log", false);

// Walk the Asure AD user list
BufferedReader br = new BufferedReader(new FileReader(args[2]));
String line = "";

br.readLine(); // skip header
while ((line = br.readLine()) != null) {

try {

// use comma as separator
String[] items = line.split(",");
String fName = "";
if (items.length >= 1 && items[0] != null) { fName = items[0].replaceAll("\"", ""); }
String lName = "";
if (items.length >= 2 && items[1] != null) { lName = items[1].replaceAll("\"", ""); }
String eMail = "";
if (items.length >= 3 && items[2] != null) { eMail = items[2].replaceAll("\"", ""); }

User u = usersManager.loadUserByEmail(eMail);

if (u == null && eMail.length() > 0) {

u = new User(eMail, lName + ", " + fName, "Participant");
usersManager.createUser(u, false);

System.out.println("");
System.out.println("*** New User Created: " + lName + ", " + fName);

logWriter.append("New User Created: " + lName + ", " + fName);
logWriter.append(System.getProperty( "line.separator" ));

}

} catch (Exception e) {

if (e instanceof RequestFailedException) {

System.out.println(((RequestFailedException)e).getFailureBody());

} else {

System.out.println(e.getMessage());

}

}
}
} catch (Exception e) {

System.out.println(e.getMessage());

}
finally {
try {

logWriter.flush();
logWriter.close();

}
catch (IOException e) {

e.printStackTrace();

}
}
}
