import httpx
import sys

# Step 1: Login
res = httpx.post('http://localhost:3001/api/users/login', json={'email': '402707192@qq.com', 'password': '123123'})
token = res.json()['token']
headers = {'Authorization': f'JWT {token}'}

for category, collection_name in [
    ('imm-pathways', 'ca_imm-pathways'),
    ('edu-school-planning', 'ca_edu-school-planning')
]:
    print(f"\n=== Processing {category} -> {collection_name} ===")
    res = httpx.get(f'http://localhost:3001/api/books?where[category][equals]={category}&limit=200', headers=headers)
    payload_books = res.json()['docs']
    print(f'Found {len(payload_books)} {category} books in Payload')

    for b in payload_books:
        print(f"[RUN] {b['engineBookId']} -> {collection_name}")
        try:
            r = httpx.post(
                'http://localhost:8001/engine/ingest',
                json={
                    'book_id': b['id'],
                    'title': b['engineBookId'],
                    'category': category,
                    'force_parse': False,
                    'collection_name': collection_name
                },
                timeout=30.0
            )
            print(r.status_code, r.json() if r.status_code == 200 else r.text)
        except Exception as e:
            print('Error:', e)
