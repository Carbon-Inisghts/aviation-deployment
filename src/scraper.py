from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
import time


# Supabase credentials
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_api_key"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set up WebDriver
service = EdgeService(EdgeChromiumDriverManager().install())
driver = webdriver.Edge(service=service)

# Open the target URL
url = 'https://www.eurocontrol.int/Economics/DailyTrafficVariation-States.html'
driver.get(url)

# Wait for the page to load
time.sleep(5)  # Adjust based on the page loading time

# Parse the page content
soup = BeautifulSoup(driver.page_source, 'html.parser')

chart_div = soup.find('div', {'id': 'MyGeoEntityChart_div'})

if chart_div:
    table = chart_div.find('table')

    if table:
        # Extract table headers
        headers = [th.text.strip() for th in table.find('thead').find_all('th')]

        # Extract rows
        rows = []
        for tr in table.find('tbody').find_all('tr'):
            cells = [td.text.strip() for td in tr.find_all('td')]
            row_data = dict(zip(headers, cells))  # Convert row to a dictionary
            rows.append(row_data)

        # Filter the rows by country
        allowed_countries = [
            'Austria', 'Belgium', 'Bulgaria', 'Czech Republic', 'Denmark', 'Germany', 'Greece', 'Estonia', 'Spain', 'Finland', 'France', 'Cyprus', 'Croatia', 
            'Hungary', 'Ireland', 'Italy', 'Lithuania', 'Luxembourg', 'Latvia', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Sweden', 'Slovenia', 
            'Slovakia', 'Malta'
        ]
        filtered_rows = [row for row in rows if row.get('Entity') in allowed_countries]

        # Add yesterday's date to each row and format the Flights column
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        for row in filtered_rows:
            # Format Flights column
            if 'Flights' in row:
                row['Flights'] = row['Flights'].replace(",", ".")
            row['Date'] = yesterday
            row['Emission'] = row['Flights'] * 4.88 #emission 

        # Insert data into Supabase
        for row in filtered_rows:
            response = supabase.table('aviation_emission').insert(row).execute()
            if response.get('error'):
                print(f"Error inserting row: {response['error']}")
            else:
                print(f"Inserted row: {row}")
    else:
        print("Table not found inside chart_div.")
else:
    print("Chart div not found.")

# Close the WebDriver session
driver.quit()

