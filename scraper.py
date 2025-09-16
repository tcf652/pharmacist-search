import requests
from bs4 import BeautifulSoup
import pandas as pd
import time  # For adding delays to avoid overloading the site

def scrape_pharmacists(letter):
    url = f"https://www.ppbhk.org.hk/eng/list_pharmacists/list.php?key={letter}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error for bad responses
    except requests.RequestException as e:
        print(f"Error fetching {letter}: {e}")
        return pd.DataFrame()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print(f"No table found for {letter}")
        return pd.DataFrame()
    
    # Extract headers and rows
    headers = [th.text.strip() for th in table.find_all('th')]
    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip header row
        row = [td.text.strip() for td in tr.find_all('td')]
        if row:  # Skip empty rows
            rows.append(row)
    
    df = pd.DataFrame(rows, columns=headers)
    time.sleep(1)  # Delay to be polite to the server
    return df

def scrape_all_pharmacists():
    all_dfs = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        print(f"Scraping letter {letter}...")
        df = scrape_pharmacists(letter)
        if not df.empty:
            all_dfs.append(df)
    
    if all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True)
        full_df.to_csv('pharmacists.csv', index=False)  # Save to CSV for reuse
        return full_df
    else:
        print("No data scraped.")
        return pd.DataFrame()

def search_pharmacist(df, name):
    # Case-insensitive search on 'Name' column, handling English/Chinese
    results = df[df['Name'].str.contains(name, case=False, na=False)]
    if results.empty:
        print(f"No matches found for '{name}'.")
    else:
        print(results.to_markdown(index=False))

if __name__ == "__main__":
    # Scrape and save data (run this once, then load from CSV for future searches)
    df = scrape_all_pharmacists()
    
    # Or load from existing CSV to avoid rescraping
    # df = pd.read_csv('pharmacists.csv')
    
    # Example search (replace with your input)
    search_name = input("Enter pharmacist name to search: ")
    search_pharmacist(df, search_name)
