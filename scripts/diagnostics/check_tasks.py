"""Check ingest-tasks and books data in Payload CMS."""
import requests

PAYLOAD_URL = "http://localhost:3001"
EMAIL = "402707192@qq.com"
PASSWORD = "123123"

def main():
    import io, sys
    out = io.StringIO()
    _print = lambda *a, **kw: print(*a, **kw, file=out)

    # 1. Login
    r = requests.post(f"{PAYLOAD_URL}/api/users/login", json={"email": EMAIL, "password": PASSWORD})
    token = r.json().get("token")
    if not token:
        _print("Login failed:", r.text)
        return
    _print("✅ Logged in\n")
    headers = {"Authorization": f"JWT {token}"}

    # 2. Check ingest-tasks
    _print("=== INGEST TASKS ===")
    r = requests.get(f"{PAYLOAD_URL}/api/ingest-tasks", params={"limit": 20, "depth": 1, "sort": "-createdAt"}, headers=headers)
    data = r.json()
    _print(f"Total: {data.get('totalDocs', 0)}")
    for t in data.get("docs", []):
        book = t.get("book")
        book_title = book.get("title") if isinstance(book, dict) else book
        _print(f"  [{t['id']}] type={t['taskType']} status={t['status']} progress={t['progress']}% book={book_title}")
    if not data.get("docs"):
        _print("  (no records)")

    # 3. Check books with pipeline
    _print("\n=== BOOKS (with pipeline) ===")
    r = requests.get(f"{PAYLOAD_URL}/api/books", params={"limit": 20, "depth": 0}, headers=headers)
    data = r.json()
    _print(f"Total: {data.get('totalDocs', 0)}")
    for b in data.get("docs", []):
        p = b.get("pipeline", {})
        _print(f"  [{b['id']}] \"{b['title']}\" status={b.get('status')} pipeline={p}")

    # Write to file
    with open("scripts/check_tasks_output.txt", "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print("Output written to scripts/check_tasks_output.txt")

if __name__ == "__main__":
    main()
