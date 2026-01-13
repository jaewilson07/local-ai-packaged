---
title: "SNIPPET - Regex // Regular Expressions"
url: /c/developerdomocom-community-edition/regex-code-snippets
author: Jae Myong Wilson
published_date: Jun 14, 2021
updated_date: Oct 11, 2021 at 09:37 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
likes: 1
---
# SNIPPET - Regex // Regular Expressions
**Author:** Jae Myong Wilson
**Published:** Jun 14, 2021
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

Remove non-ASCII values

[^\x00-\x7F]+

﻿

[

](#remove-attachment)

[

![](https://cdn.sstatic.net/Sites/stackoverflow/Img/apple-touch-icon@2.png?v=73d79a89bded)

How do I remove all non-ASCII characters with regex and Notepad++?

I searched a lot, but nowhere is it written how to remove non-ASCII characters from Notepad++.

I need to know what command to write in find and replace (with picture it would be great).
If I want...

https://stackoverflow.com/questions/20889996/how-do-i-remove-all-non-ascii-characters-with-regex-and-notepad

](https://stackoverflow.com/questions/20889996/how-do-i-remove-all-non-ascii-characters-with-regex-and-notepad)

﻿

## **Parsing Social Data**

From Domo Dojo
[https://dojo.domo.com/discussion/38198/some-useful-regex-statements#latest](https://dojo.domo.com/discussion/38198/some-useful-regex-statements#latest)

### **Get Handles**

(^|\s|[^[@\w])+[^](https://dojo.domo.com/profile/%5Cw%5D%29%2B%5B%5E)[@\s]+](https://dojo.domo.com/profile/%5Cs%5D%2B)

*Example:* Hi [@Something](https://dojo.domo.com/profile/Something) how are [@you](https://dojo.domo.com/profile/you) doing David.
*Result:* [@Something](https://dojo.domo.com/profile/Something) [@you
](https://dojo.domo.com/profile/you)

### **Get Hastags:**

(^|\s|[^#\w])+[^#\s]+

*Example:* Hi #Something how are #you doing David.
*Result:* #Something #you

### **Remove Handles:**

(?=([@\w+\b))](https://dojo.domo.com/profile/%5Cw%2B%5Cb%29%29)

*Example:* Hi [@Something](https://dojo.domo.com/profile/Something) how are [@you](https://dojo.domo.com/profile/you) doing David.
*Result:* Hi how are doing David.

### **Remove Hashtags:**

(?=(#\w+\b))

*Example:* Hi #Something how are #you doing David.
*Result:* Hi how are doing David

### **Get a word or phrase:**

\b(?!cat\b)\w+

*Example:* This cat is beautiful!!

*Result:* cat

### **Except a word or phrase:**

\b(?=cat\b)\w+

*Example:* This cat is beautiful!!
*Result:* This is beautiful!!

### **Get Character(s):**

### **Get 1st  four characters (including space)**

(?<=.{4}).+

*Example:* This cat is beautiful!!
*Result:* This

### ***Get last four characters (including space)***

.+(?=.{4})

*Example:* This cat is beautiful!!
*Result:* ul!!

### **Select all the characters before a character or word:**

.*are)

*Example:* Hi #Something how are #you doing David.
*Result:* Hi #Something how

**Select all the characters after a character or word:**

are.*

*Example:* Hi #Something how are #you doing David.
*Result:* #you doing David.
