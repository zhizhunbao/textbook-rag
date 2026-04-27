"""
Rebuild topic_index.json from ALL books in data/mineru_output/.

Reads each book's content_list.json to extract chapter/section structure,
then maps chapters to topics using keyword matching against a comprehensive
topic taxonomy.

Produces a compact index: topic → [{ book, subject, chapter, title }]
No sections array (the full content is accessible via the markdown files).

Usage:
    uv run python scripts/rebuild_topic_index.py
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# ── Configuration ──
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MINERU_DIR = BASE_DIR / "data" / "mineru_output"
OUTPUT_FILE = BASE_DIR / "data" / "topic_index.json"

# Max chapters to extract per book (real books have 10-30 chapters)
MAX_CHAPTERS_PER_BOOK = 50

# ── Book Registry ──
BOOK_REGISTRY = {
    # Python
    "ramalho_fluent_python": {"key": "fluent_python", "subject": "python"},
    "beazley_python_cookbook": {"key": "python_cookbook", "subject": "python"},
    "downey_think_python_2e": {"key": "think_python", "subject": "python"},
    "downey_how_to_think_like_cs": {"key": "think_cs", "subject": "python"},
    "okken_python_testing_pytest": {"key": "okken_pytest", "subject": "python"},
    "percival_cosmic_python": {"key": "cosmic_python", "subject": "python"},
    # JavaScript
    "flanagan_js_definitive_guide": {"key": "flanagan_js", "subject": "javascript"},
    "haverbeke_eloquent_javascript": {"key": "eloquent_js", "subject": "javascript"},
    "simpson_ydkjs_up_going": {"key": "ydkjs_up_going", "subject": "javascript"},
    "simpson_ydkjs_scope_closures": {"key": "ydkjs_scope", "subject": "javascript"},
    "simpson_ydkjs_this_object_prototypes": {"key": "ydkjs_this", "subject": "javascript"},
    "simpson_ydkjs_types_grammar": {"key": "ydkjs_types", "subject": "javascript"},
    "simpson_ydkjs_async_performance": {"key": "ydkjs_async", "subject": "javascript"},
    "simpson_ydkjs_es6_beyond": {"key": "ydkjs_es6", "subject": "javascript"},
    # TypeScript
    "basarat_typescript_deep_dive": {"key": "ts_deep_dive", "subject": "typescript"},
    # Algorithms
    "cormen_CLRS": {"key": "clrs", "subject": "algorithms"},
    # ML
    "goodfellow_deep_learning": {"key": "goodfellow", "subject": "ml"},
    "bishop_prml": {"key": "bishop", "subject": "ml"},
    "hastie_esl": {"key": "esl", "subject": "ml"},
    "james_ISLR": {"key": "islr", "subject": "ml"},
    "kelleher_ml_fundamentals": {"key": "kelleher", "subject": "ml"},
    "murphy_pml1": {"key": "murphy_pml1", "subject": "ml"},
    "murphy_pml2": {"key": "murphy_pml2", "subject": "ml"},
    "barber_brml": {"key": "barber", "subject": "ml"},
    "shalev-shwartz_uml": {"key": "shalev", "subject": "ml"},
    # Math
    "deisenroth_mml": {"key": "mml", "subject": "math"},
    "boyd_convex_optimization": {"key": "boyd", "subject": "math"},
    "grinstead_snell_probability": {"key": "grinstead", "subject": "math"},
    "downey_think_stats_2e": {"key": "downey", "subject": "math"},
    "mackay_information_theory": {"key": "mackay", "subject": "math"},
    # NLP
    "jurafsky_slp3": {"key": "jurafsky", "subject": "nlp"},
    "eisenstein_nlp": {"key": "eisenstein", "subject": "nlp"},
    # IR
    "manning_intro_to_ir": {"key": "manning_ir", "subject": "ir"},
    # CV
    "szeliski_cv": {"key": "szeliski", "subject": "cv"},
    # RL
    "sutton_barto_rl_intro": {"key": "sutton", "subject": "rl"},
    # Graphs
    "hamilton_grl": {"key": "hamilton", "subject": "graphs"},
    # UX
    "krug_dont_make_me_think": {"key": "krug", "subject": "ux"},
    "norman_design_everyday_things": {"key": "norman", "subject": "ux"},
    # SE
    "martin_clean_code": {"key": "clean_code", "subject": "se"},
    "martin_clean_architecture": {"key": "clean_arch", "subject": "se"},
    "gof_design_patterns": {"key": "gof", "subject": "se"},
    "kleppmann_ddia": {"key": "ddia", "subject": "se"},
    "hunt_pragmatic_programmer": {"key": "pragmatic", "subject": "se"},
    "fowler_refactoring": {"key": "refactoring", "subject": "se"},
    "ejsmont_web_scalability": {"key": "web_scale", "subject": "se"},
    "fontaine_art_of_postgresql": {"key": "art_pg", "subject": "se"},
    "google_swe": {"key": "google_swe", "subject": "se"},
    # DevOps
    "chacon_pro_git": {"key": "pro_git", "subject": "devops"},
    "google_sre": {"key": "google_sre", "subject": "devops"},
    "nygard_release_it": {"key": "release_it", "subject": "devops"},
    # Security & Reverse Engineering
    "seitz_black_hat_python": {"key": "black_hat_python", "subject": "security"},
    "aumasson_serious_cryptography": {"key": "serious_crypto", "subject": "security"},
    "andriesse_practical_binary_analysis": {"key": "binary_analysis", "subject": "security"},
    "zalewski_tangled_web": {"key": "tangled_web", "subject": "security"},
    # Networking & Protocols
    "gourley_http_definitive_guide": {"key": "http_guide", "subject": "networking"},
    "barrett_ssh_definitive_guide": {"key": "ssh_guide", "subject": "networking"},
    # Frameworks & Tools
    "lubanovic_fastapi_modern_web": {"key": "fastapi_web", "subject": "python"},
    "kreibich_using_sqlite": {"key": "using_sqlite", "subject": "database"},
}

# ── Topic Taxonomy ──
TOPIC_KEYWORDS = {
    # --- ML/AI ---
    "neural_networks": [
        r"neural network", r"deep learning", r"backpropag", r"perceptron",
        r"multilayer", r"feedforward", r"activation function",
    ],
    "cnn": [r"convolutional", r"\bcnn\b", r"convnet", r"pooling layer"],
    "rnn": [
        r"recurrent", r"\brnn\b", r"\blstm\b", r"\bgru\b",
        r"sequence.to.sequence",
    ],
    "transformers": [
        r"transformer", r"attention mechanism", r"self.attention",
        r"multi.head attention",
    ],
    "optimization": [
        r"optimiz", r"gradient descent", r"stochastic gradient",
        r"convex optim", r"numerical computation",
    ],
    "regularization": [
        r"regulariz", r"dropout", r"weight decay", r"batch norm",
        r"early stopping",
    ],
    "generative_models": [
        r"generative model", r"generative adversarial", r"\bgan\b",
        r"\bvae\b", r"variational autoencoder", r"autoencoder",
        r"normalizing flow",
    ],
    "reinforcement_learning": [
        r"reinforcement learn", r"policy gradient",
        r"q.learning", r"markov decision", r"\bmdp\b",
        r"temporal difference", r"td.learning",
    ],
    "bayesian": [
        r"bayesian", r"posterior", r"prior.*distribut",
        r"conjugate prior",
    ],
    "classification": [
        r"classif", r"logistic regression", r"decision boundar",
        r"naive bayes", r"support vector",
    ],
    "regression": [r"regression", r"linear model", r"least squares"],
    "clustering": [
        r"cluster", r"k.means", r"mixture model", r"gaussian mixture",
        r"expectation maxim",
    ],
    "dimensionality_reduction": [
        r"dimensionality reduc", r"\bpca\b", r"principal component",
        r"\bsvd\b", r"singular value", r"manifold",
    ],
    "ensemble_methods": [
        r"ensemble", r"random forest", r"boosting", r"bagging",
        r"gradient boost",
    ],
    "kernel_methods": [r"kernel method", r"\bsvm\b", r"support vector machine"],
    "graphical_models": [
        r"graphical model", r"belief network", r"markov random field",
        r"factor graph", r"belief propagation",
    ],
    "learning_theory": [
        r"learning theory", r"pac.learn", r"vc.dimension",
        r"sample complexity", r"generalization bound",
    ],
    "inference": [
        r"variational inference", r"approximate inference",
        r"exact inference", r"\bmcmc\b", r"importance sampling",
        r"gibbs sampling",
    ],
    "probability": [
        r"probability distribut", r"random variable",
        r"expected value", r"central limit", r"law of large",
        r"probability theory",
    ],
    "linear_algebra": [
        r"linear algebra", r"matrix decompos", r"vector space",
        r"eigenvalue", r"eigenvector",
    ],
    "information_theory": [
        r"information theory", r"\bentropy\b", r"mutual information",
        r"kl.divergence",
    ],
    # --- NLP ---
    "natural_language_processing": [
        r"natural language", r"tokeniz", r"word embedding",
        r"named entity", r"dependency pars", r"language model",
    ],
    "text_classification": [
        r"text classif", r"sentiment analy", r"document classif",
    ],
    "information_retrieval": [
        r"information retrieval", r"inverted index",
        r"tf.idf", r"boolean retrieval", r"vector space model",
        r"web search",
    ],
    # --- CV ---
    "computer_vision": [
        r"computer vision", r"image process", r"object detect",
        r"segmentation", r"feature detect", r"stereo vision",
        r"3d reconstruct",
    ],
    # --- Graph ---
    "graph_learning": [
        r"graph neural", r"graph represent", r"node embedding",
        r"knowledge graph", r"graph convol",
    ],
    # --- Python ---
    "python_core": [
        r"python data model", r"pythonic", r"special method",
        r"dunder method",
    ],
    "iterators_generators": [
        r"iterator", r"generator", r"\byield\b", r"iterable protocol",
    ],
    "decorators_metaclasses": [
        r"decorator", r"metaclass", r"metaprogramming", r"descriptor protocol",
    ],
    "concurrency": [
        r"concurren", r"asyncio", r"threading", r"multiprocess",
        r"coroutine", r"parallel",
    ],
    "type_system": [
        r"type system", r"type hint", r"type guard", r"generic type",
        r"static typing",
    ],
    # --- JavaScript/TypeScript ---
    "javascript_core": [
        r"javascript.*definitive", r"ecmascript", r"es6",
        r"arrow function", r"destructuring", r"template literal",
    ],
    "scope_closures": [
        r"scope.*closure", r"lexical scope", r"block scope", r"hoisting",
    ],
    "prototypes_this": [
        r"prototype chain", r"this.*binding", r"object prototype",
        r"delegation",
    ],
    "promises_async": [
        r"promise", r"async.*await", r"callback hell",
        r"generator.*async",
    ],
    "dom_web_apis": [
        r"document object model", r"\bdom\b.*manipulat", r"web api",
        r"canvas.*draw",
    ],
    "modules": [r"module system", r"commonjs", r"\besm\b", r"import.*export"],
    "typescript": [
        r"typescript", r"type annotation", r"compiler option",
        r"declaration file",
    ],
    # --- SE / Architecture ---
    "clean_code": [
        r"clean code", r"meaningful name", r"code smell",
        r"boy scout rule",
    ],
    "refactoring": [
        r"refactor", r"extract method", r"code smell",
        r"improve.*design",
    ],
    "design_patterns": [
        r"design pattern", r"factory.*method", r"singleton",
        r"observer.*pattern", r"strategy.*pattern", r"adapter.*pattern",
        r"template method", r"creational pattern", r"structural pattern",
        r"behavioral pattern",
    ],
    "architecture": [
        r"clean architect", r"\bsolid\b.*principle", r"dependency rule",
        r"component principle", r"hexagonal", r"onion architect",
        r"microservice",
    ],
    "domain_driven_design": [
        r"domain.driven", r"\bddd\b", r"repository pattern",
        r"service layer", r"unit of work", r"bounded context",
        r"\bcqrs\b", r"event sourc",
    ],
    "distributed_systems": [
        r"distributed system", r"replication", r"partitioning",
        r"consensus", r"consistency model", r"cap theorem",
    ],
    "data_modeling": [
        r"data model", r"schema design", r"normalization",
        r"storage engine",
    ],
    "transactions": [
        r"transaction", r"\bacid\b", r"isolation level",
        r"serializ.*snapshot",
    ],
    "stream_batch_processing": [
        r"stream process", r"batch process", r"map.?reduce",
        r"message queue",
    ],
    "sql_database": [
        r"postgresql", r"query optim", r"window function",
        r"common table expression", r"\bcte\b",
        r"stored procedure",
    ],
    "algorithms_data_structures": [
        r"algorithm.*analysis", r"data structure",
        r"sorting algorithm", r"graph algorithm",
        r"dynamic programming", r"hash table",
    ],
    # --- Testing ---
    "testing": [
        r"unit test", r"integration test", r"test.driven",
        r"\bpytest\b", r"fixture", r"test coverage",
        r"parameteriz.*test",
    ],
    "code_review": [
        r"code review", r"peer review", r"pull request review",
    ],
    # --- DevOps ---
    "git_version_control": [
        r"git.*branch", r"version control system", r"\brebase\b",
        r"git.*hook", r"distributed.*version",
    ],
    "site_reliability": [
        r"site reliability", r"\bslo\b", r"error budget",
        r"incident.*response", r"postmortem",
    ],
    "monitoring_observability": [
        r"monitoring.*system", r"alerting", r"distributed tracing",
    ],
    "ci_cd_deployment": [
        r"continuous integrat", r"continuous deliver",
        r"deployment.*strateg", r"release engineer",
        r"canary.*deploy", r"blue.green",
    ],
    "stability_patterns": [
        r"circuit.?breaker", r"bulkhead.*pattern", r"timeout.*pattern",
        r"cascading failure", r"stability.*pattern",
    ],
    "scalability": [
        r"scalab.*architect", r"load balanc",
        r"horizontal scal", r"capacity plan",
    ],
    # --- UX ---
    "usability_design": [
        r"usability", r"user experience", r"navigation design",
        r"affordance", r"signifier", r"conceptual model",
        r"accessibility",
    ],
    "design_thinking": [
        r"design think", r"human.centered design", r"human error",
    ],
    # --- SE Practices ---
    "software_engineering": [
        r"software engineer", r"style guide", r"large.scale change",
        r"technical debt",
    ],
    "pragmatic_practices": [
        r"pragmatic.*program", r"orthogonality", r"tracer bullet",
        r"don.t repeat yourself",
    ],
    "error_handling": [
        r"error handl", r"exception.*handling", r"fault toler",
    ],
    # --- Security & Reverse Engineering ---
    "network_security": [
        r"network security", r"packet sniff", r"raw socket",
        r"network program", r"scapy", r"pcap",
    ],
    "cryptography": [
        r"cryptograph", r"encryption", r"decryption", r"\baes\b",
        r"block cipher", r"stream cipher", r"hash function",
        r"key derivation", r"\bpbkdf", r"\btls\b", r"\bssl\b",
        r"\brsa\b", r"elliptic curve", r"public.key", r"symmetric",
        r"asymmetric", r"digital signature", r"\bmac\b.*auth",
    ],
    "reverse_engineering": [
        r"reverse engineer", r"binary analysis", r"disassembl",
        r"debug.*binary", r"\belf\b.*format", r"\bpe\b.*format",
        r"code injection", r"binary patch", r"instrumentation",
    ],
    "web_security": [
        r"web.*security", r"\bxss\b", r"cross.site script",
        r"\bcsrf\b", r"same.origin", r"content.*sniff",
        r"cookie.*security", r"injection.*attack",
    ],
    "proxy_gateway": [
        r"\bproxy\b", r"reverse proxy", r"gateway",
        r"forward.*proxy", r"tunneling", r"man.in.the.middle",
    ],
    # --- Networking & Protocols ---
    "http_protocol": [
        r"\bhttp\b.*protocol", r"\bhttp\b.*method",
        r"header.*field", r"status.*code", r"content.*type",
        r"content.*negotiat", r"\bsse\b", r"server.sent event",
        r"chunked.*transfer", r"\brest\b.*api",
    ],
    "ssh_protocol": [
        r"\bssh\b", r"secure shell", r"port forward",
        r"\bsftp\b", r"\bscp\b", r"key.*exchange",
        r"agent.*forward", r"ssh.*tunnel",
    ],
    # --- Database ---
    "sqlite": [
        r"\bsqlite\b", r"embedded.*database", r"\bwal\b.*mode",
        r"write.ahead.*log", r"virtual.*table", r"full.text.*search",
    ],
    # --- Frameworks ---
    "fastapi": [
        r"\bfastapi\b", r"\bpydantic\b", r"dependency.*inject",
        r"\bmiddleware\b", r"async.*endpoint", r"\buvicorn\b",
        r"api.*document", r"openapi",
    ],
    # --- Protobuf ---
    "protobuf_serialization": [
        r"protocol.*buffer", r"\bprotobuf\b", r"serializ",
        r"wire.*format", r"\bvarint\b", r"binary.*encod",
    ],
}


def extract_chapters_from_content_list(content_list_path: Path) -> list[dict]:
    """
    Extract chapter structure from a MinerU content_list.json.
    Only extracts numbered chapters (ch01, ch02...) and appendices.
    Skips OCR noise like short titles and front matter.
    """
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    chapters = []
    seen_chapters = set()

    for item in content:
        if item.get("type") != "text":
            continue

        text = item.get("text", "").strip()
        if not text or item.get("text_level") != 1:
            continue

        # Skip very short or very long text (OCR noise)
        if len(text) < 5 or len(text) > 300:
            continue

        # Try Chapter N: Title
        ch_match = re.match(
            r"(?:chapter\s+)?(\d+)[\.:\s]+(.{3,120})",
            text, re.IGNORECASE,
        )
        if ch_match:
            ch_key = f"ch{ch_match.group(1).zfill(2)}"
            if ch_key not in seen_chapters:
                seen_chapters.add(ch_key)
                chapters.append({
                    "chapter": ch_key,
                    "title": ch_match.group(2).strip().rstrip(".,: "),
                })
            continue

        # Try Appendix A: Title
        app_match = re.match(
            r"appendix\s+([A-Z])[\.:\s]*(.{3,120})",
            text, re.IGNORECASE,
        )
        if app_match:
            app_key = f"app{app_match.group(1)}"
            if app_key not in seen_chapters:
                seen_chapters.add(app_key)
                chapters.append({
                    "chapter": app_key,
                    "title": app_match.group(2).strip().rstrip(".,: "),
                })

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def extract_chapters_from_markdown(md_path: Path) -> list[dict]:
    """
    Fallback: extract chapters from markdown # headings.
    Only extracts numbered chapters.
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    chapters = []
    seen_chapters = set()

    for line in lines:
        line = line.strip()
        h1_match = re.match(r"^#\s+(.+)", line)
        if not h1_match:
            continue

        title = h1_match.group(1).strip()
        if len(title) < 5 or len(title) > 200:
            continue

        ch_match = re.match(
            r"(?:chapter\s+)?(\d+)[\.:\s]+(.{3,120})",
            title, re.IGNORECASE,
        )
        if ch_match:
            ch_key = f"ch{ch_match.group(1).zfill(2)}"
            if ch_key not in seen_chapters:
                seen_chapters.add(ch_key)
                chapters.append({
                    "chapter": ch_key,
                    "title": ch_match.group(2).strip().rstrip(".,: "),
                })

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def extract_chapters_from_toc(content_list_path: Path) -> list[dict]:
    """
    Extract chapters from Table of Contents block in content_list.json.
    Many books have a single large text block that lists all chapters.
    """
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    chapters = []
    seen_chapters = set()

    for item in content:
        if item.get("type") != "text":
            continue
        text = item.get("text", "")
        # Look for a ToC-like block (multiple chapter references)
        if text.count("\n") < 3:
            continue

        # Extract "Chapter N Title" or "N Title ... page" patterns
        for match in re.finditer(
            r"(?:chapter\s+)?(\d+)[\.:\s]+([^\n]{3,80}?)(?:\s*\.{2,}\s*\d+|\s*\d+\s*$|\s*$)",
            text, re.IGNORECASE | re.MULTILINE,
        ):
            ch_num = match.group(1)
            ch_title = match.group(2).strip().rstrip(".,: ")
            ch_key = f"ch{ch_num.zfill(2)}"
            if ch_key not in seen_chapters and len(ch_title) > 2:
                seen_chapters.add(ch_key)
                chapters.append({
                    "chapter": ch_key,
                    "title": ch_title,
                })

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def match_topics(title: str) -> list[str]:
    """Match a chapter title against the topic taxonomy."""
    matched = []
    for topic, patterns in TOPIC_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                matched.append(topic)
                break
    return matched


def build_topic_index() -> dict:
    """Build the complete topic index from all books."""
    topics_map: dict[str, list] = defaultdict(list)

    book_dirs = sorted(MINERU_DIR.iterdir())
    total_books_indexed = set()

    for book_dir in book_dirs:
        if not book_dir.is_dir():
            continue

        dir_name = book_dir.name
        if dir_name not in BOOK_REGISTRY:
            print(f"  ⚠ Skipping unknown: {dir_name}")
            continue

        reg = BOOK_REGISTRY[dir_name]
        book_key = reg["key"]
        subject = reg["subject"]

        content_list = book_dir / dir_name / "auto" / f"{dir_name}_content_list.json"
        md_file = book_dir / dir_name / "auto" / f"{dir_name}.md"

        # Try multiple extraction strategies, pick the best
        ch_from_content = extract_chapters_from_content_list(content_list)
        ch_from_toc = extract_chapters_from_toc(content_list)
        ch_from_md = extract_chapters_from_markdown(md_file)

        # Use whichever gave the most numbered chapters
        candidates = [ch_from_content, ch_from_toc, ch_from_md]
        chapters = max(candidates, key=len)

        if not chapters:
            print(f"  ⚠ No chapters: {dir_name}")
            continue

        matched_count = 0
        for ch in chapters:
            matched = match_topics(ch["title"])
            for topic in matched:
                ref = {
                    "book": book_key,
                    "subject": subject,
                    "chapter": ch["chapter"],
                    "title": ch["title"],
                }
                # Deduplicate
                if not any(
                    r["book"] == book_key and r["chapter"] == ch["chapter"]
                    for r in topics_map[topic]
                ):
                    topics_map[topic].append(ref)
                    matched_count += 1

        total_books_indexed.add(book_key)
        print(f"  ✓ {dir_name}: {len(chapters)} ch, {matched_count} matches")

    # Build final structure
    final_topics = {}
    for name in sorted(topics_map):
        refs = topics_map[name]
        final_topics[name] = {"count": len(refs), "references": refs}

    total_refs = sum(t["count"] for t in final_topics.values())

    return {
        "topics": final_topics,
        "stats": {
            "total_topics": len(final_topics),
            "total_references": total_refs,
            "total_books": len(total_books_indexed),
        },
    }


def main():
    print(f"📚 Rebuilding topic_index.json from {MINERU_DIR}")
    print()

    result = build_topic_index()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    s = result["stats"]
    print()
    print(f"✅ Wrote {OUTPUT_FILE}")
    print(f"   📊 {s['total_topics']} topics, {s['total_references']} refs, "
          f"{s['total_books']} books")
    print(f"   📦 File size: {OUTPUT_FILE.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
