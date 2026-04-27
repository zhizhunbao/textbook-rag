"""
GitHub 圣经搜索器 — 从 GitHub 搜索免费权威教科书 PDF
Search GitHub for free canonical textbooks (PDF links)

Usage:
    python search_github_books.py
    python search_github_books.py --download   # 自动下载找到的 PDF
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ============================================================
# 配置：圣经级教科书清单
# official_url: 官方免费下载地址（优先使用，不需要搜索 GitHub）
# existing_files: 本地已存在的文件名（不同命名但同一本书）
# commercial: True = 商业书籍，只搜索不强制要求下载
# ============================================================
WANTED_BOOKS = [
    # ==================== Python ====================
    {
        "keywords": ["fluent python", "luciano ramalho"],
        "filename": "ramalho_fluent_python.pdf",
        "category": "python",
        "desc": "Fluent Python — Python 进阶圣经 (Luciano Ramalho)",
    },
    {
        "keywords": ["python cookbook", "david beazley"],
        "filename": "beazley_python_cookbook.pdf",
        "category": "python",
        "desc": "Python Cookbook 3rd — Python 实战圣经 (David Beazley)",
    },
    {
        "keywords": ["think python", "allen downey"],
        "filename": "downey_think_python_2e.pdf",
        "category": "python",
        "desc": "Think Python 2e — Python 入门圣经 (Allen Downey)",
        "official_url": "https://greenteapress.com/thinkpython2/thinkpython2.pdf",
        "existing_files": ["downey_think_python_2e.pdf"],
    },
    # ==================== ML / DL ====================
    {
        "keywords": ["introduction statistical learning"],
        "filename": "james_ISLR.pdf",
        "category": "ml",
        "desc": "ISLR — 统计学习圣经 (James, Witten, Hastie, Tibshirani)",
        "official_url": "https://hastie.su.domains/ISLR2/ISLRv2_corrected_June_2023.pdf",
    },
    {
        "keywords": ["elements statistical learning"],
        "filename": "hastie_ESL.pdf",
        "category": "ml",
        "desc": "ESL — 统计学习进阶圣经 (Hastie, Tibshirani, Friedman)",
        "official_url": "https://hastie.su.domains/ElemStatLearn/printings/ESLII_print12_toc.pdf",
        "existing_files": ["hastie_esl.pdf"],
    },
    {
        "keywords": ["deep learning", "goodfellow", "bengio"],
        "filename": "goodfellow_deep_learning.pdf",
        "category": "ml",
        "desc": "Deep Learning — 深度学习圣经 (Goodfellow, Bengio, Courville)",
        "official_url": "https://github.com/janishar/mit-deep-learning-book-pdf/raw/master/complete-book-pdf/deeplearningbook.pdf",
        "existing_files": ["goodfellow_deep_learning.pdf"],
    },
    {
        "keywords": ["pattern recognition", "machine learning", "bishop"],
        "filename": "bishop_PRML.pdf",
        "category": "ml",
        "desc": "PRML — 模式识别圣经 (Christopher Bishop)",
        "official_url": "https://www.microsoft.com/en-us/research/uploads/prod/2006/01/Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf",
        "existing_files": ["bishop_prml.pdf"],
    },
    {
        "keywords": ["probabilistic machine learning", "murphy"],
        "filename": "murphy_PML1.pdf",
        "category": "ml",
        "desc": "Probabilistic ML: An Introduction — 概率ML圣经 (Kevin Murphy)",
        "official_url": "https://probml.github.io/pml-book/book1.html",
        "existing_files": ["murphy_pml1.pdf"],
    },
    {
        "keywords": ["understanding machine learning", "shalev-shwartz"],
        "filename": "shalev_UML.pdf",
        "category": "ml",
        "desc": "Understanding ML — 机器学习理论圣经 (Shalev-Shwartz & Ben-David)",
        "official_url": "https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/understanding-machine-learning-theory-algorithms.pdf",
        "existing_files": ["shalev-shwartz_uml.pdf"],
    },
    # ==================== Math ====================
    {
        "keywords": ["mathematics machine learning"],
        "filename": "deisenroth_MML.pdf",
        "category": "math",
        "desc": "Mathematics for Machine Learning — ML 数学圣经 (Deisenroth)",
        "official_url": "https://mml-book.github.io/book/mml-book.pdf",
        "existing_files": ["deisenroth_mml.pdf"],
    },
    {
        "keywords": ["convex optimization", "boyd", "vandenberghe"],
        "filename": "boyd_convex_optimization.pdf",
        "category": "math",
        "desc": "Convex Optimization — 凸优化圣经 (Boyd & Vandenberghe)",
        "official_url": "https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf",
        "existing_files": ["boyd_convex_optimization.pdf"],
    },
    {
        "keywords": ["information theory", "inference", "mackay"],
        "filename": "mackay_information_theory.pdf",
        "category": "math",
        "desc": "Information Theory — 信息论圣经 (David MacKay)",
        "official_url": "https://www.inference.org.uk/itprnn/book.pdf",
        "existing_files": ["mackay_information_theory.pdf"],
    },
    {
        "keywords": ["think stats", "allen downey"],
        "filename": "downey_think_stats_2e.pdf",
        "category": "math",
        "desc": "Think Stats 2e — 统计思维入门 (Allen Downey)",
        "official_url": "https://greenteapress.com/thinkstats2/thinkstats2.pdf",
        "existing_files": ["downey_think_stats_2e.pdf"],
    },
    {
        "keywords": ["introduction to probability", "grinstead", "snell"],
        "filename": "grinstead_snell_probability.pdf",
        "category": "math",
        "desc": "Intro to Probability — 概率论入门 (Grinstead & Snell)",
        "official_url": "https://math.dartmouth.edu/~prob/prob/prob.pdf",
        "existing_files": ["grinstead_snell_probability.pdf"],
    },
    # ==================== RL ====================
    {
        "keywords": ["reinforcement learning", "introduction", "sutton", "barto"],
        "filename": "sutton_RL_intro.pdf",
        "category": "rl",
        "desc": "RL: An Introduction — 强化学习圣经 (Sutton & Barto)",
        "official_url": "http://incompleteideas.net/book/RLbook2020.pdf",
        "existing_files": ["sutton_barto_rl_intro.pdf"],
    },
    # ==================== NLP ====================
    {
        "keywords": ["speech language processing", "jurafsky"],
        "filename": "jurafsky_slp3.pdf",
        "category": "nlp",
        "desc": "SLP3 — NLP 圣经 (Jurafsky & Martin)",
        "official_url": "https://web.stanford.edu/~jurafsky/slp3/ed3bookfeb3_2024.pdf",
        "existing_files": ["jurafsky_slp3.pdf"],
    },
    {
        "keywords": ["introduction information retrieval", "manning"],
        "filename": "manning_intro_to_ir.pdf",
        "category": "nlp",
        "desc": "Intro to IR — 信息检索圣经 (Manning, Raghavan, Schütze)",
        "official_url": "https://nlp.stanford.edu/IR-book/pdf/irbookonlinereading.pdf",
        "existing_files": ["manning_intro_to_ir.pdf"],
    },
    {
        "keywords": ["nlp", "eisenstein"],
        "filename": "eisenstein_nlp.pdf",
        "category": "nlp",
        "desc": "NLP Notes — NLP 教程 (Jacob Eisenstein)",
        "official_url": "https://github.com/jacobeisenstein/gt-nlp-class/blob/master/notes/eisenstein-nlp-notes.pdf?raw=true",
        "existing_files": ["eisenstein_nlp.pdf"],
    },
    # ==================== CV / MV ====================
    {
        "keywords": ["computer vision", "algorithms applications", "szeliski"],
        "filename": "szeliski_cv.pdf",
        "category": "cv",
        "desc": "Computer Vision — 计算机视觉圣经 (Richard Szeliski)",
        "official_url": "https://szeliski.org/Book/szeliski20Book.pdf",
        "existing_files": ["szeliski_cv.pdf"],
    },
    # ==================== JavaScript ====================
    {
        "keywords": ["eloquent javascript", "haverbeke"],
        "filename": "haverbeke_eloquent_javascript.pdf",
        "category": "webdev",
        "desc": "Eloquent JavaScript — JS 入门圣经 (Marijn Haverbeke)",
        "official_url": "https://eloquentjavascript.net/Eloquent_JavaScript.pdf",
    },
    {
        "keywords": ["javascript definitive guide", "flanagan"],
        "filename": "flanagan_js_definitive_guide.pdf",
        "category": "webdev",
        "desc": "JavaScript: The Definitive Guide — JS 犀牛书 (David Flanagan)",
        "commercial": True,
    },
    {
        "keywords": ["you don't know js", "kyle simpson"],
        "filename": "simpson_ydkjs.pdf",
        "category": "webdev",
        "desc": "You Don't Know JS — JS 深入圣经 (Kyle Simpson)",
        "commercial": True,
    },
    # ==================== UI / UX ====================
    {
        "keywords": ["don't make me think", "steve krug"],
        "filename": "krug_dont_make_me_think.pdf",
        "category": "uiux",
        "desc": "Don't Make Me Think — Web 可用性圣经 (Steve Krug)",
        "commercial": True,
    },
    {
        "keywords": ["design of everyday things", "don norman"],
        "filename": "norman_design_everyday_things.pdf",
        "category": "uiux",
        "desc": "The Design of Everyday Things — 设计圣经 (Don Norman)",
        "commercial": True,
    },
    # ==================== 算法 ====================
    {
        "keywords": ["introduction to algorithms", "cormen"],
        "filename": "cormen_CLRS.pdf",
        "category": "math",
        "desc": "CLRS — 算法导论 (Cormen, Leiserson, Rivest, Stein)",
        "commercial": True,
    },
]

# 知名的免费编程书籍 GitHub 仓库
KNOWN_REPOS = [
    "EbookFoundation/free-programming-books",
]

BASE_DIR = Path(__file__).parent.parent.parent / "data" / "raw_pdfs"
CATEGORY_DIRS = {
    "python": BASE_DIR / "textbooks",
    "ml": BASE_DIR / "textbooks",
    "math": BASE_DIR / "textbooks",
    "rl": BASE_DIR / "textbooks",
    "nlp": BASE_DIR / "textbooks",
    "cv": BASE_DIR / "textbooks",
    "webdev": BASE_DIR / "textbooks",
    "uiux": BASE_DIR / "textbooks",
}


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def github_api(endpoint, params=None):
    """Call GitHub API (authenticated, higher rate limit)."""
    url = f"https://api.github.com{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BookSearchScript/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ⚠️  GitHub API rate limit hit. Waiting 60s...")
            time.sleep(60)
            return github_api(endpoint, params)
        raise


def search_github_code(keywords):
    """Search GitHub code for PDF links matching keywords.
    在 GitHub 代码中搜索包含关键词的 PDF 链接
    """
    query = " ".join(keywords) + " extension:md pdf"
    results = github_api("/search/code", {
        "q": query,
        "per_page": 10,
    })
    return results.get("items", [])


def search_github_repos(keywords):
    """Search GitHub repos matching keywords.
    搜索与关键词匹配的 GitHub 仓库
    """
    query = " ".join(keywords) + " free book pdf"
    results = github_api("/search/repositories", {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5,
    })
    return results.get("items", [])


def extract_pdf_urls(text):
    """Extract PDF URLs from markdown text.
    从 markdown 文本中提取 PDF URL
    """
    # Match URLs ending in .pdf
    pdf_pattern = r'https?://[^\s\)\]\"\'<>]+\.pdf(?:\?[^\s\)\]\"\'<>]*)?'
    urls = re.findall(pdf_pattern, text, re.IGNORECASE)
    # Also match common PDF hosting patterns
    # 也匹配常见的 PDF 托管模式
    hosting_patterns = [
        r'https?://arxiv\.org/pdf/[\d\.]+',
        r'https?://papers\.nips\.cc/[^\s\)\]\"\'<>]+\.pdf',
        r'https?://[^\s]+\.github\.io/[^\s\)\]\"\'<>]+\.pdf',
    ]
    for pat in hosting_patterns:
        urls.extend(re.findall(pat, text, re.IGNORECASE))
    return list(set(urls))


def fetch_raw_content(item):
    """Fetch raw content of a GitHub code search result.
    获取 GitHub 代码搜索结果的原始内容
    """
    # Build raw URL from html_url
    html_url = item.get("html_url", "")
    raw_url = html_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "BookSearchScript/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def keywords_match(text, keywords):
    """Check if all keywords appear in text (case-insensitive).
    检查文本中是否包含所有关键词（不区分大小写）
    """
    text_lower = text.lower()
    return all(kw.lower() in text_lower for kw in keywords)


def download_pdf(url, filepath):
    """Download a PDF file.
    下载 PDF 文件
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            if len(data) < 10000:  # Too small, probably not a real PDF
                print(f"    ⚠️  File too small ({len(data)} bytes), skipping")
                return False
            # Check PDF magic bytes
            if not data[:4] == b'%PDF':
                print(f"    ⚠️  Not a valid PDF file, skipping")
                return False
            with open(filepath, 'wb') as f:
                f.write(data)
            size_mb = round(len(data) / (1024 * 1024), 1)
            print(f"    ✅ Downloaded: {filepath.name} ({size_mb} MB)")
            return True
    except Exception as e:
        print(f"    ❌ Download failed: {e}")
        return False


def _check_existing(book):
    """Check if the book already exists locally (possibly under a different name).
    检查本地是否已存在该书（可能文件名不同）
    """
    dest_dir = CATEGORY_DIRS.get(book["category"], BASE_DIR)
    # Check canonical filename / 检查标准文件名
    dest_path = dest_dir / book["filename"]
    if dest_path.exists():
        return dest_path
    # Check alternate filenames / 检查可能的别名
    for alt in book.get("existing_files", []):
        alt_path = dest_dir / alt
        if alt_path.exists():
            return alt_path
    return None


def search_one_book(book, do_download=False):
    """Search for one book across GitHub.
    在 GitHub 上搜索一本书
    """
    print(f"\n📖 {book['desc']}")

    # === Check if already exists locally ===
    existing = _check_existing(book)
    if existing:
        print(f"   ✅ Already have: {existing}")
        return [str(existing)]

    # === Commercial book — search only, no download expected ===
    if book.get("commercial"):
        print(f"   💰 Commercial book — 需购买或图书馆借阅")
        return []

    # === Strategy 0: Official free URL (最优先) ===
    official_url = book.get("official_url")
    if official_url:
        print(f"   🎯 官方免费地址: {official_url}")
        if do_download:
            dest_dir = CATEGORY_DIRS.get(book["category"], BASE_DIR)
            dest_path = dest_dir / book["filename"]
            print(f"   ⬇️  Downloading from official source...")
            download_pdf(official_url, dest_path)
        return [official_url]

    # === No official URL — search GitHub ===
    print(f"   Keywords: {book['keywords']}")
    found_urls = []

    # Strategy 1: Search GitHub code
    print("   🔍 Searching GitHub code...")
    try:
        items = search_github_code(book["keywords"])
        for item in items[:5]:
            content = fetch_raw_content(item)
            if content and keywords_match(content, book["keywords"]):
                urls = extract_pdf_urls(content)
                for u in urls:
                    if keywords_match(u, book["keywords"][:1]):
                        found_urls.append(u)
                    elif any(kw.lower().replace(" ", "") in u.lower() for kw in book["keywords"][:1]):
                        found_urls.append(u)
                if urls:
                    found_urls.extend(urls[:3])
        time.sleep(6)
    except Exception as e:
        print(f"   ⚠️  Code search error: {e}")
        time.sleep(6)

    # Strategy 2: Search repos
    print("   🔍 Searching GitHub repos...")
    try:
        repos = search_github_repos(book["keywords"])
        for repo in repos[:3]:
            print(f"      📦 {repo['full_name']} ⭐{repo.get('stargazers_count', 0)}")
            try:
                readme = github_api(f"/repos/{repo['full_name']}/readme")
                if readme and "download_url" in readme:
                    content = ""
                    try:
                        req = urllib.request.Request(readme["download_url"],
                                                   headers={"User-Agent": "BookSearchScript/1.0"})
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            content = resp.read().decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                    if content:
                        urls = extract_pdf_urls(content)
                        found_urls.extend(urls[:5])
            except Exception:
                pass
        time.sleep(6)
    except Exception as e:
        print(f"   ⚠️  Repo search error: {e}")
        time.sleep(6)

    # Deduplicate
    seen = set()
    unique_urls = []
    for u in found_urls:
        u_clean = u.rstrip("/").rstrip(".")
        if u_clean not in seen and len(u_clean) > 20:
            seen.add(u_clean)
            unique_urls.append(u_clean)

    if unique_urls:
        print(f"   📋 Found {len(unique_urls)} PDF link(s):")
        for i, u in enumerate(unique_urls[:10]):
            print(f"      [{i+1}] {u}")

        if do_download and unique_urls:
            dest_dir = CATEGORY_DIRS.get(book["category"], BASE_DIR)
            dest_path = dest_dir / book["filename"]
            if dest_path.exists():
                print(f"   ⏭️  Already exists: {dest_path}")
            else:
                for u in unique_urls[:5]:
                    print(f"   ⬇️  Trying: {u}")
                    if download_pdf(u, dest_path):
                        break
    else:
        print("   ❌ No PDF links found (商业书籍，需购买或图书馆借阅)")

    return unique_urls


def main():
    do_download = "--download" in sys.argv
    print("=" * 65)
    print("  📚 GitHub 圣经搜索器 — Free Textbook PDF Finder")
    print("=" * 65)
    if do_download:
        print("  Mode: SEARCH + DOWNLOAD")
        # Ensure directories exist / 确保目录存在
        for d in CATEGORY_DIRS.values():
            d.mkdir(parents=True, exist_ok=True)
    else:
        print("  Mode: SEARCH ONLY (use --download to auto-download)")
    print(f"  Searching for {len(WANTED_BOOKS)} books...\n")

    all_results = {}
    for book in WANTED_BOOKS:
        urls = search_one_book(book, do_download)
        all_results[book["desc"]] = urls

    # Summary / 总结
    print("\n" + "=" * 65)
    print("  📊 搜索结果总结 / Search Summary")
    print("=" * 65)
    found = 0
    not_found = 0
    commercial = 0
    for book in WANTED_BOOKS:
        desc = book["desc"]
        urls = all_results.get(desc, [])
        if book.get("commercial"):
            print(f"  💰 {desc}")
            commercial += 1
        elif urls:
            print(f"  ✅ {desc}")
            found += 1
        else:
            print(f"  ❌ {desc}")
            not_found += 1
    print(f"\n  Found/Have: {found}/{len(WANTED_BOOKS)} books")
    print(f"  Missing: {not_found} books (free but not yet downloaded)")
    print(f"  Commercial: {commercial} books (需购买或图书馆借阅)")

    if not do_download and found > 0:
        print(f"\n  💡 Run with --download to auto-download found PDFs:")
        print(f"     python {Path(__file__).name} --download")

    # Save results to JSON for clean review / 保存结果到 JSON 文件
    results_file = BASE_DIR / "search_results.json"
    json_out = {
        "found_count": found,
        "total_count": len(WANTED_BOOKS),
        "results": {desc: urls for desc, urls in all_results.items()},
    }
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
