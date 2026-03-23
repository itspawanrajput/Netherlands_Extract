import requests
import json

def test_honda():
    url = 'https://www.honda.nl/content/honda/nl_nl/cars/find-a-dealer/_jcr_content/fad2.dealers.JSON'
    headers = {
        'accept': '*/*',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'origin': 'https://www.honda.nl',
        'referer': 'https://www.honda.nl/cars/find-a-dealer.html',
    }
    
    # Using requests to send multipart/form-data
    files = {
        'q': (None, 'Netherlands'),
        'filters': (None, 'SALES')
    }
    
    r = requests.post(url, headers=headers, files=files)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Count: {len(data)}")
        if len(data) > 0:
            print("First item name:", data[0]['dealer']['name'])
            # Save for inspection
            with open("honda_nl_test.json", "w") as f:
                json.dump(data, f, indent=2)

if __name__ == "__main__":
    test_honda()
