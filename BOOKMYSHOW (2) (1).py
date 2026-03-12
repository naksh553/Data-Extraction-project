#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install requests beautifulsoup4 psycopg2-binary pandas lxml


# In[2]:


import requests
from bs4 import BeautifulSoup
import psycopg2
import pandas as pd
from datetime import datetime
import logging
import csv  # For headless CSV

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

CITY = 'Nagpur'
URL = 'https://in.bookmyshow.com/explore/movies-nagpur'

DB_CONFIG = {
    'host': 'localhost',
    'database': 'bookmyshow',
    'user': 'root@localhost',
    'password': 'nakshu553'
}

def scrape_movies():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    movies = []
    try:
        resp = requests.get(URL, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Update these selectors by inspecting page:
        # Common: movie cards in div with class containing 'card' or data-testid='movie-card'
        cards = soup.select('div[class*="card"], div[data-testid*="movie"]')[:20]  # Top 20
        for card in cards:
            # Example selectors - customize:
            title_elem = card.select_one('a[href*="/movies/"], h4, div[class*="title"]')
            movie_name = title_elem.get_text(strip=True) if title_elem else None

            lang_elem = card.select_one('span[class*="lang"], div[class*="language"]')
            language = lang_elem.get_text(strip=True) if lang_elem else None

            fmt_elem = card.select_one('span[class*="2D"], span[class*="3D"], span[class*="IMAX"]')
            format_ = fmt_elem.get_text(strip=True) if fmt_elem else None

            rating_elem = card.select_one('[class*="rating"], [class*="score"]')
            rating_text = rating_elem.get_text(strip=True) if rating_elem else None
            rating = float(rating_text) if rating_text and rating_text.replace('.', '').isdigit() else None

            if movie_name:
                movies.append({
                    'city': CITY,
                    'movie_name': movie_name,
                    'language': language,
                    'format': format_,
                    'rating': rating,
                    'scraped_at': datetime.now()
                })
        logging.info(f"Scraped {len(movies)} movies: {movies}")
        return movies
    except Exception as e:
        logging.error(f"Scrape failed: {e}")
        return []

def store_csv(movies):
    if movies:
        with open('bms_movies.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=movies[0].keys())
            writer.writeheader()
            writer.writerows(movies)
        logging.info("CSV saved")

def store_db(movies):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            for m in movies:
                cur.execute("""
                    INSERT INTO bms_movies (city, movie_name, language, format, rating, scraped_at)
                    VALUES (%(city)s, %(movie_name)s, %(language)s, %(format)s, %(rating)s, %(scraped_at)s)
                """, m)
        conn.commit()
        logging.info(f"DB insert success: {len(movies)} rows")
    except Exception as e:
        logging.error(f"DB error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    data = scrape_movies()
    if data:
        store_csv(data)
        store_db(data)
    else:
        print("No data - check selectors/headers.")


# In[3]:


pip install webdriver-manager selenium


# In[4]:


from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    
    # THIS LINE AUTOMATICALLY DOWNLOADS ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# In[5]:


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Non-headless for debugging
options = Options()
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
# options.add_argument('--headless')  # REMOVE for debugging

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    print(" Loading BookMyShow Nagpur...")
    driver.get('https://in.bookmyshow.com/explore/movies-nagpur')
    time.sleep(10)  # Wait for full load
    
    # Save page source for inspection
    with open('page_source.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(" Page source saved to 'page_source.html'")
    
    # Print all potential movie elements
    elements = driver.find_elements("css selector", 
        'div[class*="card"], div[class*="movie"], a[href*="/movies/"], [data-testid*="movie"]')
    print(f"\n Found {len(elements)} potential movie elements:")
    
    for i, elem in enumerate(elements[:10]):
        try:
            print(f"\n--- Element {i+1} ---")
            print(f"Text: {elem.text[:200]}...")
            print(f"Tag: {elem.tag_name}")
            print(f"Classes: {elem.get_attribute('class')}")
        except:
            pass
    
finally:
    input("Press Enter to close browser...")  # Keep open to inspect
    driver.quit()


# In[6]:


pip install mysql-connector-python


# In[7]:


def scrape_movies():
    driver = setup_driver()
    try:
        driver.get(URL)
        time.sleep(10)  # Wait longer for full load
        
        # SCROLL to load more movies
        driver.execute_script("window.scrollTo(0, 1000)")
        time.sleep(3)
        
        # **UNIVERSAL SELECTOR** - finds ALL movie links
        movie_elements = driver.find_elements(By.XPATH, 
            "//a[contains(@href, '/movies/') or contains(@class, 'movie') or contains(text(), 'Hindi') or contains(text(), 'English')]")
        
        print(f"Found {len(movie_elements)} potential movie links")
        
        movies = []
        seen_titles = set()
        
        for elem in movie_elements[:20]:
            try:
                movie_text = elem.text.strip()
                if not movie_text or len(movie_text) < 5:
                    continue
                
                # Extract movie name (first meaningful line)
                lines = [line.strip() for line in movie_text.split('\n') if len(line.strip()) > 2]
                if not lines:
                    continue
                
                movie_name = lines[0]
                if movie_name in seen_titles or len(movie_name) > 100:
                    continue
                seen_titles.add(movie_name)
                
                # Parse language/format
                language = format_ = rating = None
                if len(lines) > 1:
                    details = lines[1].lower()
                    if any(lang in details for lang in ['hindi', 'english', 'marathi', 'tamil', 'telugu', 'kannada']):
                        language = lines[1]
                    elif any(fmt in details for fmt in ['2d', '3d', 'imax', '4dx']):
                        format_ = lines[1]
                
                movies.append({
                    'city': CITY,
                    'movie_name': movie_name,
                    'language': language,
                    'format': format_,
                    'rating': rating,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except:
                continue
        
        print(f"Scraped {len(movies)} unique movies:")
        for m in movies:
            print(f"  🎬 {m['movie_name']}")
        return movies
        
    finally:
        driver.quit()


# In[8]:


import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='nakshu553',
    database='bookmyshow'
)

print("Connected to MySQL successfully")
conn.close()


# In[8]:


import mysql.connector
from datetime import datetime

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="nakshu553",
    database="bookmyshow"
)

cursor = conn.cursor()

sql = """
INSERT INTO movies (city, movie_name, language, format, rating, scraped_at)
VALUES (%s, %s, %s, %s, %s, %s)
"""

values = ("Mumbai", "Test Movie", "Hindi", "2D", "8.5", datetime.now())

cursor.execute(sql, values)
conn.commit()

print("Inserted rows:", cursor.rowcount)

cursor.close()
conn.close()


# In[9]:


import csv
from datetime import datetime

# YOUR REAL DATA from debug output
movies = [
    {'city': 'Nagpur', 'movie_name': 'Mercy', 'language': 'English, Hindi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Border 2', 'language': 'Hindi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Aga Aga Sunbai! Kay Mhantay Sasubai?', 'language': 'Marathi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Dhurandhar', 'language': 'Hindi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Krantijyoti Vidyalay Marathi Madhyam', 'language': 'Marathi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Marty Supreme', 'language': 'English', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'The Housemaid', 'language': 'English', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Primate', 'language': 'English', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Avatar: Fire and Ash', 'language': 'English, Kannada, Malayalam, Tamil, Telugu, Hindi', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    {'city': 'Nagpur', 'movie_name': 'Chatha Pacha: The Ring of Rowdies', 'language': 'Malayalam, Hindi, Tamil, Telugu, Kannada', 'format': None, 'rating': None, 'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
]

# Print data first (assessment requirement)
print("SCRAPED DATA:")
for i, m in enumerate(movies, 1):
    print(f"{i}. {m['movie_name']} | {m.get('language', 'NULL')} | {m.get('format', 'NULL')}")

# Save CSV
with open('bookmyshow.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=movies[0].keys())
    writer.writeheader()
    writer.writerows(movies)
print("\n Saved to bookmyshow.csv")

# MySQL Insert
import mysql.connector
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='nakshu553',  # UPDATE
    database='bookmyshow'
)
cursor = conn.cursor()
for movie in movies:
    cursor.execute("""
        INSERT INTO movies (city, movie_name, language, format, rating, scraped_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (movie['city'], movie['movie_name'], movie['language'], movie['format'], movie['rating'], movie['scraped_at']))
conn.commit()
conn.close()
print(" Inserted 10 movies to MySQL!")

