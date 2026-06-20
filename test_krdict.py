import requests

response = requests.get(
    "http://krdict.korean.go.kr/api/search",
    params={
        "key": "10C0546A14DB2730C63BC2E0E08022A5",
        "q": "진짜"
    }
)

print(response.status_code)
print(response.text[:300])