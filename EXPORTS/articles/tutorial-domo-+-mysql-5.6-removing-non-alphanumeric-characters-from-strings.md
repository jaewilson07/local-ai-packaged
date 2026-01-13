---
title: "TUTORIAL -- Domo + MySQL 5.6 - Removing non alphanumeric characters from strings"
url: /c/developerdomocom-community-edition/removing-non-alphanumeric-characters-from-strings-in-domo
author: Jae Myong Wilson
published_date: May 11, 2021
updated_date: Nov 26, 2022 at 11:00 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
comments: 1
---
# TUTORIAL -- Domo + MySQL 5.6 - Removing non alphanumeric characters from strings
**Author:** Jae Myong Wilson
**Published:** May 11, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

![Cover Image](https://app.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBL3dXREE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--b3ad3bbf3b1dba6cfabd34c37b6b616622da8398/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJYW5CbkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--a9f899a0c764220ba5650fc8daea690765ef2c6f/Luma%20(9).jpg)

---

# Searching for permutations of empty string

Sometimes when you upload data to Domo the space, new line, or carriage return comes in 'weird' making them difficult to excise from your data

use

- STR_TO_CHARNAMES

- STR_TO_HEX

## Regex Replace in MySQL 5.6

MySQL 5.6 doesn't have a regex replace function.  Here's a function that will do it for you.

[https://stackoverflow.com/questions/986826/how-to-do-a-regular-expression-replace-in-mysql](https://stackoverflow.com/questions/986826/how-to-do-a-regular-expression-replace-in-mysql)

call the procedure

SELECT regex_replace('[^a-zA-Z0-9/ \\-]', '' ,`Row_Name`) as test

create the function

CREATE FUNCTION  `regex_replace`(pattern VARCHAR(1000),replacement VARCHAR(1000),original VARCHAR(1000))
RETURNS VARCHAR(1000)
DETERMINISTIC
BEGIN
DECLARE temp VARCHAR(1000);
DECLARE ch VARCHAR(1);
DECLARE i INT;
SET i = 1;
SET temp = '';
IF original REGEXP pattern THEN
loop_label: LOOP
IF i>CHAR_LENGTH(original) THEN
LEAVE loop_label;
END IF;
SET ch = SUBSTRING(original,i,1);
IF NOT ch REGEXP pattern THEN
SET temp = CONCAT(temp,ch);
ELSE
SET temp = CONCAT(temp,replacement);
END IF;
SET i=i+1;
END LOOP;
ELSE
SET temp = original;
END IF;
RETURN temp;
END

# Regex in MagicETL 1.0 using Capture Groups

- Then, type or copy the following regular expression into the box labeled **Enter a term to search for**: **^http[s]?://([a-zA-Z0-9\-\.]*).*$**The ^ symbol indicates you want the pattern to start with what comes after this. The start of any matching value will have to be "http", followed by an optional "s", since web addresses may or may not have an "s". The "?" indicates that what preceeds it is optional. The value must then have "://".Now we use parentheses to indicate that we want to remember or capture a section of the value for future use. This is called a capture group.Inside the parentheses you have indicated that the URL can have any lower case characters, any upper case characters, any digits 0-9, a hyphen, or a period. It will then look for any number of those characters together.After the capture group, the pattern indicates that there may or may not be other characters before the text value ends. The $ indicates that in order to be considered a match, nothing else can come after the part of the text that matches the pattern. In other words, because of the "^" and "$" characters, the pattern provided must match the entire value in the column, not just a part of it.

﻿

[

](#remove-attachment)

[](#left)
[](#full_width)

![](https://datacrew.circle.so/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBeVdYQ3c9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--0cc43b39663d250eb7ff805110de243b647c1a14/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBTU0lJY0c1bkJqb0dSVlE2RkhKbGMybDZaVjkwYjE5c2FXMXBkRnNIYVFJNEJEQTZDbk5oZG1WeWV3WTZDbk4wY21sd1ZBPT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--7535ef66ff04b52d1ea165e904a77a64f9cc7389/Untitled.png)
﻿
In the **Replace found term with** box, type "$1". This $1 references the first capture group in your pattern. Using it here indicates that you want to replace the value that matches the entire regex pattern with what you've captured in the capture group. In this example, that means replacing the entire URL with just the domain.
