import os
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

KEYWORDS = ['data analyst']
LOCATION = 'United States'
SKILLS = ['SQL', 'Python', 'Excel', 'R', 'Tableau', 'Power BI']

def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(service=Service(), options=chrome_options)

# ---------- INDEED ----------
def scrape_indeed(pages=2):
    print("[*] Scraping Indeed...")
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []

    for page in range(0, pages * 10, 10):
        url = f"https://www.indeed.com/jobs?q=data+analyst&start={page}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div.job_seen_beacon')

        for card in cards:
            try:
                title = card.find('h2').text.strip()
                if 'data analyst' not in title.lower(): continue
                company = card.find('span', class_='companyName').text.strip()
                location = card.find('div', class_='companyLocation').text.strip()
                salary = card.find('div', class_='salary-snippet')
                desc = card.find('div', class_='job-snippet').text.strip()

                results.append({
                    'Job Title': title,
                    'Company': company,
                    'Location': location,
                    'Salary': salary.text.strip() if salary else "Not mentioned",
                    'Skills Required': ', '.join([s for s in SKILLS if s.lower() in desc.lower()]),
                    'Experience Level': guess_experience(desc)
                })
            except Exception as e:
                print("Skipped a card due to error:", e)
        time.sleep(1)

    return results

# ---------- LINKEDIN ----------
def scrape_linkedin(limit=15):
    print("[*] Scraping LinkedIn (manual login needed)...")
    driver = setup_driver(headless=False)
    driver.get("https://www.linkedin.com/login")
    input(">> Log in, then press Enter...")

    driver.get(f"https://www.linkedin.com/jobs/search/?keywords=data%20analyst&location={LOCATION}")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "job-card-container--clickable")))
    jobs = []

    job_cards = driver.find_elements(By.CLASS_NAME, "job-card-container--clickable")[:limit]
    for card in job_cards:
        try:
            driver.execute_script("arguments[0].click();", card)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "topcard__title")))
            title = driver.find_element(By.CLASS_NAME, "topcard__title").text
            if 'data analyst' not in title.lower(): continue

            company = driver.find_element(By.CLASS_NAME, "topcard__org-name-link").text
            location = driver.find_element(By.CLASS_NAME, "topcard__flavor--bullet").text
            desc = driver.find_element(By.CLASS_NAME, "description__text").text

            jobs.append({
                'Job Title': title,
                'Company': company,
                'Location': location,
                'Salary': "Not mentioned",
                'Skills Required': ', '.join([s for s in SKILLS if s.lower() in desc.lower()]),
                'Experience Level': guess_experience(desc)
            })
        except Exception as e:
            print("Skipped a LinkedIn post due to:", e)

    driver.quit()
    return jobs

# ---------- GLASSDOOR ----------
def scrape_glassdoor(limit=10):
    print("[*] Scraping Glassdoor (manual login needed)...")
    driver = setup_driver(headless=False)
    driver.get("https://www.glassdoor.com/Job/data-analyst-jobs-SRCH_KO0,12.htm")
    input(">> Log in if prompted, then press Enter...")

    jobs = []
    job_cards = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "react-job-listing")))[:limit]

    for card in job_cards:
        try:
            driver.execute_script("arguments[0].click();", card)
            time.sleep(3)
            title = driver.find_element(By.CLASS_NAME, "css-17x2pwl").text
            if 'data analyst' not in title.lower(): continue
            company = driver.find_element(By.CLASS_NAME, "css-87uc0g").text
            location = driver.find_element(By.CLASS_NAME, "css-56kyx5").text
            salary_els = driver.find_elements(By.CLASS_NAME, "css-1bluz6i")
            desc = driver.find_element(By.CLASS_NAME, "jobDescriptionContent").text

            jobs.append({
                'Job Title': title,
                'Company': company,
                'Location': location,
                'Salary': salary_els[0].text if salary_els else "Not mentioned",
                'Skills Required': ', '.join([s for s in SKILLS if s.lower() in desc.lower()]),
                'Experience Level': guess_experience(desc)
            })
        except Exception as e:
            print("Skipped Glassdoor card due to:", e)
    driver.quit()
    return jobs

# ---------- Experience Helper ----------
def guess_experience(text):
    text = text.lower()
    if 'senior' in text or '5+' in text or 'lead' in text:
        return 'Senior'
    elif 'mid' in text or '3+' in text:
        return 'Mid'
    else:
        return 'Entry'

# ---------- Export ----------
def export_to_csv(all_jobs):
    df = pd.DataFrame(all_jobs)
    os.makedirs("output", exist_ok=True)
    df.to_csv("output/all_data_analyst_jobs.csv", index=False)
    print("[✓] Data saved to output/all_data_analyst_jobs.csv")

# ---------- Main ----------
if __name__ == "__main__":
    jobs = []
    jobs += scrape_indeed()
    jobs += scrape_linkedin()
    jobs += scrape_glassdoor()
    export_to_csv(jobs)
