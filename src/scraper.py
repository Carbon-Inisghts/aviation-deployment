from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
import time 
import pandas as pd
from dotenv import load_dotenv
import os

# Supabase credentials
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) 

# Set up WebDriver
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = EdgeService(EdgeChromiumDriverManager().install())
driver = webdriver.Edge(service=service)

# Open the target URL
url = 'https://www.eurocontrol.int/Economics/DailyTrafficVariation-States.html'
driver.get(url)

time.sleep(5) # Wait for the page to load

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
        Countries = [
            'Austria', 'Belgium', 'Bulgaria', 'Czech Republic', 'Denmark', 'Germany', 'Greece', 'Estonia', 'Spain', 'Finland', 'France', 'Cyprus', 'Croatia',
            'Hungary', 'Ireland', 'Italy', 'Lithuania', 'Luxembourg', 'Latvia', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Sweden', 'Slovenia',
            'Slovakia', 'Malta']

        filtered_rows = [row for row in rows if row.get('Entity') in Countries]

        # Process the rows
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        processed_rows = []
        for row in filtered_rows:
            if 'Flights' in row:
                row['Flights'] = float(row['Flights'].replace(",", "."))
            
            processed_row = {
                'Date': yesterday,
                'Entity': row['Entity'],
                'Flights': row['Flights'],
                'Emission': row['Flights'] * 4.88  # Example factor
            }

            processed_rows.append(processed_row)

        # Convert to a DataFrame for aggregation
        df = pd.DataFrame(processed_rows)

        # Aggregate flights and emissions for EU27
        daily_aggregates = df.groupby('Date').agg(
            Flights=('Flights', 'sum'),
            Emission=('Emission', 'sum')
        ).reset_index()
        daily_aggregates['Entity'] = 'EU27'

        # Add EU27 data to the original processed rows
        for _, agg_row in daily_aggregates.iterrows():
            processed_rows.append({
                'Date': agg_row['Date'],  # Changed from 'Day' to 'Date'
                'Entity': agg_row['Entity'],
                'Flights': agg_row['Flights'],
                'Emission': agg_row['Emission']
            })

        # See final results
        print("\nFinal Results (Processed Rows):")
        for row in processed_rows:
            print(row)

        # Insert data into Supabase
        for row in processed_rows:
            try:
                response = supabase.table('aviation_emission').insert(row).execute()
                if response.data :
                    print(f"Inserted row: {row}")
                else:
                    print(f"Error inserting batch: {response}")
            except Exception as e:
                print(f"Error inserting batch: {e}")
    else:
        print("Table not found inside chart_div.")
else:
    print("Chart div not found.")

# Close the WebDriver session
driver.quit()
