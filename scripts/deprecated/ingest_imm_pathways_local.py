import httpx
import sys
import asyncio
from engine_v2.ingestion.pipeline import ingest_book
from engine_v2.settings import init_settings

init_settings()

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
            # Run ingest_book locally instead of hitting the engine API
            ingest_book(
                book_id=b['id'],
                book_dir_name=b['engineBookId'],
                category=category,
                task_id=None,
                collection_name=collection_name
            )
            print(f"Success: {b['engineBookId']}")
        except Exception as e:
            print('Error:', e)
