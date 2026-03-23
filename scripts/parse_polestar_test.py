import json
from bs4 import BeautifulSoup

def extract():
    with open("polestar_nl.html", "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        text = script.string
        if text and text.strip().startswith("window.__remixContext ="):
            data = text.strip()
            data = data[len("window.__remixContext = "):]
            if data.endswith(";"):
                data = data[:-1]
            try:
                j = json.loads(data)
                with open("polestar_test.json", "w", encoding="utf-8") as out:
                    json.dump(j, out, indent=2)
                print("Successfully extracted state to polestar_test.json")
                return
            except Exception as e:
                print("JSON parse error:", e)
    print("Script not found")

if __name__ == "__main__":
    extract()
