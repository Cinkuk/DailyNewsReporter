# Daily Report: A personal infomation assitant

## Project Vision
A light-weight, clear-architecture, develop-friendly personal information assitant which able to obtain information widely and generate a clear report.

## Tech Stack
 - **Python**: Python 3.12

## Module Map
 - `/data/raw_archive/<date>`: obtained raw information in the same day. Date format is YYYY-MM-DD-HH
 - `/data/report_archive/`: store each report generated. each report is HTML format. name format: <date>.html
 - `/data/latest_point`: a json file. Record latest time of obtained items of each feed
 - `/data/feeds.txt`: a json file. Record each fees's name and url, format: <name>: <url>
 - `/src`: project source code 
 - `/test`: testcase and test code
 - `/launch.py`: the one-time launch point of program
 - `/API_KEYS.txt`: store API key, format: ARK_API_KEY=<ARK_API_KEY>
 - `/topics.txt`: seletec topics, format: <topic_name>: [ON | OFF]

## Program Procedure
1. Get API_KEY from `API_KEYS.txt`
2. Get information from each feed
3. filter information: drop items later than latest point, save items newer items into disk and update `/data/latest_point`
4. drop items which are not relative to seleted topics via LLM
5. generate summary of each item via LLM. each summary should no more than 300 words. append summary into HTML document

## Data Flow
 - feed items: Web -> `/data/raw_archive/`
 - filter items: `/data/raw_archive/<date>` -> `/data/temp/`
 - generate summary: `/data/temp` -> `/data/report_archive`

## Basic Data Structure
 - item: 
```
<feed>:{
time: <release_time>,
content: <content>
}
```
 - latest_point:
```
<feed>: <YYYY-MM-DD-HH-MM>
```

## TODO
 - [ ] record `title, content, category, summary` after each generation for future model training, change design of data flow
 - [ ] add new feature: send email after HTML report generated
 - [ ] train two model to classify content and generate summary


## Agent Behaviour Standard
 - Follow `README.md` strictly
 - follow `TODO.list` as excecuting plan strictly
 - While finish each item in `TODO.list`, REMENBER to update `TODO.list` and report current step in chat
 - BEFORE write procedure code, WRITE TESTCASE and TESTCODE FIRST!!!
 - NEVER access files out of project directory!!!
 - Before each step, report your plan briefly first
 - If file is places in wrong path, move them into correct path
 - Chat with user in CHINESE
