---
title: "[Video Tutorial] Sync Domo Jupyter with GitHub"
url: /c/developerdomocom-community-edition/video-tutorial-sync-domo-jupyter-with-github
author: Jae Myong Wilson
published_date: Dec 2, 2022
updated_date: Dec 02, 2022 at 07:44 AM
tags: ['Freelancer', 'Admin', 'Domo Sensei']
categories: ['Tutorials and Code Snippets']
---
# [Video Tutorial] Sync Domo Jupyter with GitHub
**Author:** Jae Myong Wilson
**Published:** Dec 2, 2022
**Tags:** Freelancer, Admin, Domo Sensei
**Categories:** Tutorials and Code Snippets

---

# Domo Jupyter + Git

Domo Jupyter natively supports configuring and maintaining git repositories within the Jupyter environment via Terminal.

Once configured the repo can push updates to public GitHub via standard Git operations.

For use with BitBucket or other privately hosted GitHub-styled tools, Domo has 4 IPs that should be added to the enterprise-allow list.

﻿

﻿

## Generate an SSH key in DomoJupyter > Terminal

Set your user email and name (information so Git knows who's making the commit to the local repo)

git config --global [user.email](https://user.email) "[you@example.com](mailto:you@example.com)"
git config --global [user.name](https://user.name) "Your Name"
Generate your SSH key which will authenticate your push request to GitHub (confirms that you / DomoJupyter are allowed t update the repo hosted in GitHub.com

ssh-keygen -t ed25519 -C "[your_email@example.com](mailto:your_email@example.com)"
This command will create a two files on your computer, the .pub file has your public key. (the value will be a string AND your email.  You need to keep both.

If you cannot see the file in the browser, to print the contents of the file, navigate to the appropriate directory where the file is saved and run **cat**

cd .ssh
cat <file_name>

## Store the Public SSH Key in Github

⚠️Use your public key, stored in the .pub file, make sure to include the sha string and your email

For your public github account, the generated public key can be added here:[ ](https://urldefense.com/v3/__https:/github.com/settings/keys__;!!JmoZiZGBv3RvKRSx!56m1a9jtBjWCF-1mudjT5YvpW7XSXmyazc5ZajCzVjuEPvqGRqGmMnAl8sD97Vu9AH5BNsCKVVOE52xgB9vtCOUrRg%24)[https://github.com/settings/keys](https://github.com/settings/keys)

## Create your Repo in DomoJupyter and push to GitHub

⚠️ Add the SSH Remote (not HTTPS)

echo "# domo_github_sync" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin [git@github.com](mailto:git@github.com):jaewilson07/domo_github_sync.git
git push -u origin main
## Standard Domo KBs

Main document:[ https://domohelp.domo.com/hc/en-us/articles/360047400753-Jupyter-Workspaces](https://urldefense.com/v3/__https:/domohelp.domo.com/hc/en-us/articles/360047400753-Jupyter-Workspaces__;!!JmoZiZGBv3RvKRSx!56m1a9jtBjWCF-1mudjT5YvpW7XSXmyazc5ZajCzVjuEPvqGRqGmMnAl8sD97Vu9AH5BNsCKVVOE52xgB9tIFqB2UA%24)

Troubleshooting Guide:[ ](https://urldefense.com/v3/__https:/domohelp.domo.com/hc/en-us/articles/7440921035671-Jupyter-Troubleshooting-Guide-__;!!JmoZiZGBv3RvKRSx!56m1a9jtBjWCF-1mudjT5YvpW7XSXmyazc5ZajCzVjuEPvqGRqGmMnAl8sD97Vu9AH5BNsCKVVOE52xgB9s7MsVvPQ%24)

[https://domohelp.domo.com/hc/en-us/articles/7440921035671-Jupyter-Troubleshooting-Guide-
](https://urldefense.com/v3/__https:/domohelp.domo.com/hc/en-us/articles/7440921035671-Jupyter-Troubleshooting-Guide-__;!!JmoZiZGBv3RvKRSx!56m1a9jtBjWCF-1mudjT5YvpW7XSXmyazc5ZajCzVjuEPvqGRqGmMnAl8sD97Vu9AH5BNsCKVVOE52xgB9s7MsVvPQ%24)

### Cloning Repos into DomoJupyter

Once SSH key has been saved in DomoJupyter, you can take the reverse steps to clone an existing GitHub repo into DomoJupyter

git clone [https://github.com/YOUR-USERNAME/YOUR-REPOSITORY](https://github.com/YOUR-USERNAME/YOUR-REPOSITORY)

﻿

[

](#remove-attachment)

[

![](https://github.githubassets.com/images/modules/open_graph/github-logo.png)

Cloning a repository - GitHub Docs

https://ghdocs-prod.azurewebsites.net/en/repositories/creating-and-managing-repositories/cloning-a-repository

](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

﻿
