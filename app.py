from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

PHARMACIST_LIST_URL = "https://www.ppbhk.org.hk/eng/list_pharmacists/list.php"

def fetch_pharmacist_list():
    response = requests.get(PHARMACIST_LIST_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "table_list"})
    pharmacists = []
    if table:
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if cols:
                pharmacists.append({
                    "Reg. No.": cols[0],
                    "Name": cols[1],
                    "Address": cols[2],
                    "Qualification": cols[3] if len(cols) > 3 else "",
                })
    return pharmacists

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").lower()
    pharmacists = fetch_pharmacist_list()
    results = [p for p in pharmacists if query in p["Name"].lower()]
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
