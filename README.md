<h1 align="center">
  <a href="https://github.com/nekkitl/frogy"><img src="/libs/logo.png" alt="frogy"></a>
  </h1>
<h4 align="center"> Made from 🇮🇳, forked by 🇷🇺 with ❤️</h4>
My goal is to create an open-source Attack Surface Management solution and make it capable to find all the IPs, domains, subdomains, live websites, login portals for one company.  <br/><p style="font-size:10px; color: #555">Original text from src-git</p>

---

### Why was the project forked?

Yo, I'm Nick, and I was disappointed by the lack of support for macOS.
We all know that many programs, for various reasons, can be built and run fine on the Mac. Basically, this project was released for Deb-based OS, but one night I rewrote and reworked the project for full Mac compatibility.

And i think that we need faster method to provide information to frogy. See usage for details.

_glhf, bruh_ 👽

---

### How it can help a large company (Some usecases):

- **Vulnerability management team:** Can use the result to feed into their known and unknown assets database to increase their vulnerability scanning coverage.
- **Threat intel team:** Can use the result to feed into their intel DB to prioritize proactive monitoring for critical assets.
- **Asset inventory team:** Can use the result to keep their asset inventory database up-to-date by adding new unknown assets facing Internet and finding contact information for the assets inside your organization.
- **SOC team:** Can use the result to identify what all assets they are monitoring vs. not monitoring and then increase their coverage slowly.
- **Patch management team:** Many large organizations are unaware of their legacy, abandoned assets facing the Internet; they can utilize this result to identify what assets need to be taken offline if they are not being used.<br/>

It has multiple use cases depending your organization's processes and technology landscpae.

### Logic:

<img src="https://user-images.githubusercontent.com/8291014/196818780-7335b67d-1fc2-4b19-9e46-0e7813fbd8ee.jpg" alt="Frogy" title="Frogy" />

### Features:

- :frog: Horizontal subdomain enumeration
- :frog: Vertical subdomain enumeration
- :frog: Resolving subdomains to IP
- :frog: Identifying live web applications
- :frog: Identifying all the contextual properties of the web application such as title, content lenght, server, IP, cname, etc. (through httpx tool)
- :cat: Added arguments for script

### Installation:

```sh
git clone https://github.com/nekkitl/frogy.git && cd frogy && chmod +x install.sh && bash install.sh
```

### Usage:

```sh
./frogy.sh [root-domain] [organisation name] [CHAOS dataset]
        -h | Root-domain is: "example.com"
           | Organisation is: "Internet Assigned Numbers Authority" : can be skipped.
           | Is this program is in the CHAOS dataset? ["y"/"n"] : default NO

./frogy.sh "example.com" "Internet Assigned Numbers Authority"
           | or
./frogy.sh example.com
```

## Demo:

<br/><img src="https://user-images.githubusercontent.com/8291014/148625824-0760f6fe-6d8f-4217-85e7-1432388b1ee9.png" alt="Frogy" title="Frogy" height=600px />

## Output:

Output file will be saved inside the `output/<company_name>/outut.csv` folder. Where `company_name` is any company name which you give as an input to `Organization Name` at the start of the script.

---

#### A very warm thanks to the authors of the tools used in this script.

Initial repo created - A few weeks back below date.<br/>

- Date - 4 March 2019, Open-sourced
- Date - 19 March 2021, Major changes
- Date - 30 July 2023, forked for macOS

Logo credit - [www.designevo.com](http://designevo.com)

---

#### Additional:

![Viewers](https://profile-counter.glitch.me/nekkitl/count.svg)

`nekkitl` a.k.a. **Nick Ognev**, 2023q3

- Read before all: [Warning / Disclaimer](https://nekkit.xyz/Disclaimer.html)
- [Multilink](https://me.nekkit.xyz) my to other media

#### More for macOS:

[![ReadMe Card](https://github-readme-stats.vercel.app/api/pin/?username=nekkitl&repo=macfx)](https://github.com/nekkitl/macfx)
