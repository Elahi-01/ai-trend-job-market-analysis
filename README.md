# AI Trend Job Market Analysis

**Version:** 1.0.1  
**Developed by:** MD FAZLEY ELAHI

AI Trend Job Market Analysis is a Flask-based web application for analyzing job market trends using scraped job data from LinkedIn and Indeed. The system collects job listings, stores them in MongoDB, extracts important skills, and presents the results through an interactive analytics dashboard.

This project is designed mainly for **local use and demonstration purposes**, because real-time scraping from job platforms may not work properly on cloud platforms such as Railway due to browser restrictions, anti-bot protection, or dynamic website behavior.

## Project Overview

The main goal of this project is to understand current job market trends by collecting and analyzing job posting data.

The system can help identify:

- Which skills are most in demand
- Which companies are hiring
- Which locations have more job opportunities
- How many jobs are remote or on-site
- Job posting trends over time
- Source-wise job distribution from LinkedIn and Indeed

## Core Features

- LinkedIn and Indeed job scraping using Playwright and BeautifulSoup
- Keyword-only search mode
- Keyword + location search mode
- Static demo mode with sample data
- MongoDB database integration
- Duplicate job prevention using unique job IDs
- Skill extraction from job titles and descriptions
- Real-time dashboard using Chart.js
- Daily, weekly, and monthly analytics structure
- Job listing page with search and filtering
- CSV export for real scraped jobs
- Public suggestion/feedback system
- Admin login system
- Admin-only workflow page
- Demo data and real data separation

## Tech Stack

### Backend

- Python
- Flask
- Flask-CORS
- PyMongo
- APScheduler

### Database

- MongoDB
- MongoDB Atlas or Local MongoDB

### Web Scraping

- Playwright
- BeautifulSoup4

### Data Analysis

- Pandas
- NumPy
- MongoDB Aggregation Pipeline

### Frontend

- HTML
- CSS
- JavaScript
- Chart.js
- Bootstrap

## Project Workflow

The project follows this workflow:

User enters keyword and location  
↓  
Flask receives scraping request  
↓  
Scraping service starts  
↓  
LinkedIn / Indeed scraper runs  
↓  
Playwright opens browser and loads job pages  
↓  
BeautifulSoup parses job data  
↓  
Job title, company, location, salary, URL and skills are extracted  
↓  
Clean job data is prepared using JobModel  
↓  
MongoDB stores the data  
↓  
Duplicate jobs are skipped  
↓  
Analytics engine processes the stored data  
↓  
Dashboard displays charts and job market insights

## Folder Structure

ai_trend_job_market_analysis/  
│  
├── run.py  
├── seed_demo.py  
├── requirements.txt  
├── .env.example  
├── README.md  
│  
├── config/  
│ └── settings.py  
│  
└── app/  
├── \__init_\_.py  
│  
├── database/  
│ └── connection.py  
│  
├── models/  
│ └── job_model.py  
│  
├── scrapers/  
│ ├── linkedin_scraper.py  
│ └── indeed_scraper.py  
│  
├── services/  
│ ├── scraping_service.py  
│ ├── demo_data.py  
│ └── email_service.py  
│  
├── analysis/  
│ └── analytics_engine.py  
│  
├── scheduler/  
│ └── tasks.py  
│  
├── routes/  
│ ├── dashboard.py  
│ ├── jobs.py  
│ ├── analytics.py  
│ ├── scraper.py  
│ ├── messages.py  
│ └── admin.py  
│  
├── utils/  
│ ├── skill_extractor.py  
│ ├── helpers.py  
│ ├── json.py  
│ └── admin_auth.py  
│  
├── templates/  
└── static/

## Installation and Run on Windows CMD

First, open CMD in the project directory and run the following commands:

cd ai_trend_job_market_analysis  
<br/>py -m venv .venv  
<br/>.venv\\Scripts\\activate  
<br/>python -m pip install --upgrade pip  
<br/>pip install -r requirements.txt  
<br/>python -m playwright install chromium  
<br/>copy .env.example .env  
<br/>python seed_demo.py  
<br/>python run.py

Then open the application in your browser:

<http://127.0.0.1:5000>

## Environment Variables

Before running the project, create a .env file from .env.example.

Important environment variables:

SECRET_KEY=change-this-secret-key  
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/job_market_analyzer  
DATABASE_NAME=job_market_analyzer  
<br/>ADMIN_USERNAME=admin  
ADMIN_PASSWORD=change-this-admin-password

If you want to use local MongoDB, you can use:

MONGO_URI=mongodb://localhost:27017/job_market_analyzer  
DATABASE_NAME=job_market_analyzer

## Demo Mode

This project includes a static demo mode. Demo mode is useful for testing the dashboard without running live scraping.

To insert demo data:

python seed_demo.py

Then run the app:

python run.py

Open demo dashboard:

<http://127.0.0.1:5000/dashboard/demo>

## Real Data and Demo Data Separation

The project keeps real scraped data and demo data separated.

Demo data uses:

search_mode = demo  
is_demo = true  
data_scope = demo

Important separation rules:

- /dashboard shows only real scraped job data
- /dashboard/demo shows only demo data
- /jobs excludes demo records
- /jobs/export exports only real scraped jobs
- Demo records do not mix with real analytics
- CSV export filename starts with real*jobs_export*

## Search Modes

The project supports three search modes:

### 1\. Keyword + Location Search

Example:

Keyword: Python Developer  
Location: Dhaka

This mode searches job listings based on both keyword and location.

### 2\. Keyword Only Search

Example:

Keyword: Data Analyst

This mode searches jobs based only on the keyword.

### 3\. Static Demo Mode

This mode does not scrape live websites. It loads predefined sample job data for dashboard demonstration.

## Main Pages

### Dashboard

<http://127.0.0.1:5000/dashboard>

Shows real scraped job analytics.

### Demo Dashboard

<http://127.0.0.1:5000/dashboard/demo>

Shows demo-only analytics.

### Jobs Page

<http://127.0.0.1:5000/jobs>

Shows job listings with search and filter options.

### Analytics Page

<http://127.0.0.1:5000/analytics>

Shows detailed analytics and historical insights.

### Feedback Page

<http://127.0.0.1:5000/feedback>

Allows users to submit suggestions or feedback.

### Admin Login

<http://127.0.0.1:5000/admin/login>

### Admin Workflow Page

<http://127.0.0.1:5000/admin/workflow>

This page is private and only accessible after admin login.

## Manual Analytics API Test

You can manually generate analytics snapshots using these commands:

curl -X POST <http://127.0.0.1:5000/analytics/api/generate/daily>  
<br/>curl -X POST <http://127.0.0.1:5000/analytics/api/generate/weekly>  
<br/>curl -X POST <http://127.0.0.1:5000/analytics/api/generate/monthly>  
<br/>curl <http://127.0.0.1:5000/analytics/api/historical>

## Suggestion Email System

The public feedback page allows users to submit suggestions.

Every suggestion is stored in the MongoDB messages collection.

If SMTP settings are configured, the system can also send the message to the owner email.

For Gmail, use a **Gmail App Password**, not your normal Gmail password.

MAIL_ENABLED=true  
MAIL_SERVER=smtp.gmail.com  
MAIL_PORT=587  
MAIL_USE_TLS=true  
MAIL_USERNAME=<your_email@gmail.com>  
MAIL_PASSWORD=your_gmail_app_password  
MAIL_RECEIVER=<your_receiver_email@example.com>

## Important Note About Live Scraping

This project uses Playwright to scrape job websites such as LinkedIn and Indeed.

Live scraping may not always work because these platforms often use:

- Dynamic page loading
- Anti-bot protection
- Login restrictions
- Frequent HTML structure changes
- Cloud browser limitations

For this reason, this project is recommended to run locally for testing, learning, and demonstration.

Cloud deployment is not included in this README because real-time scraping may not work reliably on platforms such as Railway.

## GitHub Upload Safety

Before uploading this project to GitHub, make sure the .env file is not uploaded.

Your .gitignore should include:

.env  
\__pycache_\_/  
\*.pyc  
.venv/  
venv/  
.vscode/  
\*.db  
.DS_Store

Upload .env.example, but never upload .env.

## Useful Commands

### Run Project

python run.py

### Seed Demo Data

python seed_demo.py

### Install Playwright Browser

python -m playwright install chromium

### Export Real Jobs

Open in browser:

<http://127.0.0.1:5000/jobs/export>

## Limitations

- Live scraping depends on LinkedIn and Indeed page structure
- Scrapers may need updates if website HTML changes
- Some job websites may block automated browser activity
- Cloud platforms may not support real-time scraping properly
- MongoDB connection is required to run the full application
- Demo mode is for dashboard testing only

## Future Improvements

Possible future improvements:

- Add more job sources
- Improve skill extraction accuracy
- Add user authentication
- Add advanced filtering
- Add salary prediction
- Add AI-based job trend forecasting
- Add resume-skill matching system
- Add better scraper error handling
- Add API-based job data source support

## Developer

**MD FAZLEY ELAHI**

This project was developed as a job market analysis dashboard using Flask, MongoDB, Playwright, and Chart.js.

## Version

v1.0.1