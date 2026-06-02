"""Build the book corpus directly from Google Books search (Plan B).

Instead of one targeted lookup per known book (~2.3 requests/book), this
paginates Google Books search by subject — 40 books per request — so a full
~10k-book corpus costs only a few hundred requests. Each volume already carries
the fields the team pipeline needs (description + categories) plus rating,
thumbnail, ISBN, etc., in Google's native taxonomy (so the eval test queries
match without a mapper).

Resumable (per-page cursor), deduped (by ISBN-13 / title+author), key-rotating
(GOOGLE_BOOKS_API_KEY, _2, _3, ... — each project = 1,000 requests/day).

Run from project root:
    python notebooks/_crawl_google_search.py --test    # 1 subject, 2 pages
    python notebooks/_crawl_google_search.py            # full crawl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.data.collect import _clean_html, _get_json, _make_session, GoogleQuotaExceeded

load_dotenv(config.PROJECT_ROOT / ".env")

OUT_FILE = config.INTERMEDIATE / "google_search.jsonl"
STATE_FILE = config.INTERMEDIATE / "google_search_state.json"
LOG_FILE = config.INTERMEDIATE / "google_search.log"

# Many narrow, low-overlap subjects — diversity (not quota) is what caps unique
# yield, so we cast a wide net of fine-grained genres/topics.
SUBJECTS = [
    # --- fiction sub-genres ---
    "Mystery & Detective", "Cozy Mystery", "Hardboiled Mystery", "Police Procedural",
    "Thrillers Suspense", "Legal Thriller", "Medical Thriller", "Psychological Thriller",
    "Espionage", "Science Fiction", "Space Opera", "Hard Science Fiction",
    "Time Travel Fiction", "Cyberpunk", "Apocalyptic Dystopian", "Steampunk",
    "Epic Fantasy", "Urban Fantasy", "Dark Fantasy", "Sword Sorcery", "Mythic Fantasy",
    "Paranormal Fiction", "Contemporary Romance", "Historical Romance",
    "Romantic Suspense", "Romantic Comedy", "Fantasy Romance", "Horror",
    "Supernatural Horror", "Ghost Stories", "Vampire Fiction", "Historical Fiction",
    "Literary Fiction", "Coming of Age", "Magical Realism", "Satire", "Humorous Fiction",
    "Crime", "Noir Fiction", "War Military Fiction", "Adventure", "Sea Stories",
    "Westerns", "Short Stories", "Anthologies", "Family Life Fiction",
    "Psychological Fiction", "Gothic", "Fairy Tales Folklore", "Mythology Fiction",
    "Dystopian", "Sports Fiction", "Cultural Heritage Fiction", "Small Town Fiction",
    "Epistolary Fiction", "Political Fiction", "Religious Fiction", "Christian Fiction",
    # --- YA / children ---
    "Young Adult Romance", "Young Adult Fantasy", "Young Adult Dystopian",
    "Young Adult Contemporary", "Young Adult Science Fiction", "Juvenile Fiction",
    "Juvenile Fantasy Magic", "Middle Grade", "Children's Adventure",
    # --- nonfiction: people & history ---
    "Biography Autobiography", "Memoir", "Ancient History", "Medieval History",
    "Modern History", "Military History", "World War II History", "American History",
    "European History", "Asian History", "Historical Biography",
    # --- nonfiction: science & tech ---
    "Physics", "Astronomy Cosmology", "Biology Life Sciences", "Chemistry",
    "Mathematics", "Computers", "Artificial Intelligence", "Programming",
    "Technology Engineering", "Environmental Science", "Neuroscience", "Evolution",
    "Popular Science",
    # --- nonfiction: mind & self ---
    "Self-Help", "Psychology", "Cognitive Psychology", "Personal Development",
    "Mindfulness Meditation", "Motivational", "Habits Productivity",
    # --- nonfiction: society & money ---
    "Business Economics", "Entrepreneurship", "Personal Finance", "Investing",
    "Leadership", "Management", "Marketing", "Political Science", "Sociology",
    "Social Science", "Anthropology", "Education", "Law", "Journalism",
    # --- nonfiction: arts & living ---
    "Philosophy", "Ethics", "Religion", "Christianity", "Buddhism", "Spirituality",
    "True Crime", "Cooking", "Baking", "World Cuisine", "Travel", "Travel Writing",
    "Art", "Art History", "Photography", "Music", "Film", "Theater Drama", "Poetry",
    "Comics Graphic Novels", "Manga", "Health Fitness", "Nutrition", "Nature",
    "Gardening", "Crafts Hobbies", "Sports Recreation", "Humor", "Medical",
    "Family Relationships", "Parenting", "Pets",
]

# Round 2 expansion — the 1st run drained the SUBJECTS list (plateaued ~9.2k on
# query-diversity, NOT quota). These add NEW query axes to push toward 15-20k:
# finer sub-genres, per-author crawls (inauthor:), and free-text themes.
MORE_SUBJECTS = [
    "Regency Romance", "Cosmic Horror", "Body Horror", "Slasher", "Gothic Romance",
    "Behavioral Economics", "Military Science Fiction", "Grimdark Fantasy",
    "Portal Fantasy", "LitRPG", "Climate Fiction", "Afrofuturism", "Heist Fiction",
    "Courtroom Drama", "Spy Fiction", "Domestic Thriller", "Amateur Sleuth",
    "Caper", "Enemies to Lovers", "Workplace Romance", "Holiday Romance",
    "Sports Romance", "Paranormal Romance", "Alternate History", "First Contact",
    "Generation Ship", "Post-Apocalyptic", "Zombie Fiction", "Werewolf Fiction",
    "Witch Fiction", "Assassin Fantasy", "Pirate Fiction", "Samurai Fiction",
    "Viking Fiction", "Arthurian Legend", "Greek Mythology Retelling",
    "Norse Mythology", "Dragons Fiction", "Mermaid Fiction", "Time Slip Fiction",
    "Quantum Physics", "Cosmology", "Microbiology", "Genetics", "Climate Change",
    "Behavioral Psychology", "Social Psychology", "Game Theory", "Cryptography",
    "Machine Learning", "Data Science", "Software Engineering", "Cybersecurity",
    "Ancient Egypt", "Ancient Greece", "Ancient Rome", "Renaissance",
    "Industrial Revolution", "Cold War History", "Vietnam War", "Civil Rights Movement",
    "Espionage History", "Maritime History", "Aviation History", "Economic History",
    "Stoicism", "Existentialism", "Eastern Philosophy", "Political Philosophy",
    "Logic", "Aesthetics", "Theology", "Comparative Religion", "Mysticism",
    "Wine", "Vegetarian Cooking", "Vegan Cooking", "Bread Baking", "Desserts",
    "Mountaineering", "Wilderness Survival", "Ocean Exploration", "Birdwatching",
    "Astrophotography", "Interior Design", "Architecture", "Fashion Design",
    "Calligraphy", "Knitting", "Woodworking", "Chess", "Poker",
    "Yoga", "Running", "Weight Training", "Sleep Science", "Longevity",
    "Startups", "Venture Capital", "Negotiation", "Public Speaking",
    "Behavioral Finance", "Cryptocurrency", "Real Estate Investing",
]

# Popular authors across genres — inauthor: pulls each author's catalogue, most
# carrying clean categories + descriptions; very low overlap with subject pages.
AUTHORS = [
    # literary / contemporary fiction
    "Margaret Atwood", "Toni Morrison", "Haruki Murakami", "Gabriel Garcia Marquez",
    "Kazuo Ishiguro", "Donna Tartt", "Jonathan Franzen", "Zadie Smith",
    "Salman Rushdie", "Ian McEwan", "Cormac McCarthy", "Don DeLillo", "Philip Roth",
    "Chimamanda Ngozi Adichie", "Colson Whitehead", "Jhumpa Lahiri", "Khaled Hosseini",
    "Celeste Ng", "Hanya Yanagihara", "Sally Rooney", "Elena Ferrante", "Marilynne Robinson",
    # mystery / thriller / crime
    "Agatha Christie", "Gillian Flynn", "Lee Child", "James Patterson", "Tana French",
    "Michael Connelly", "Harlan Coben", "Dennis Lehane", "Ruth Ware", "Paula Hawkins",
    "John Grisham", "Patricia Highsmith", "Raymond Chandler", "Dashiell Hammett",
    "Karin Slaughter", "Jo Nesbo", "Stieg Larsson", "Louise Penny",
    # sci-fi / fantasy
    "Isaac Asimov", "Arthur C. Clarke", "Ursula K. Le Guin", "Philip K. Dick",
    "Frank Herbert", "Neil Gaiman", "Brandon Sanderson", "N. K. Jemisin", "Ted Chiang",
    "Liu Cixin", "Octavia Butler", "Robin Hobb", "Patrick Rothfuss", "Terry Pratchett",
    "George R. R. Martin", "Robert Jordan", "Andrzej Sapkowski", "Becky Chambers",
    "Martha Wells", "Ann Leckie", "Ray Bradbury", "Kurt Vonnegut", "Douglas Adams",
    # horror
    "Stephen King", "Shirley Jackson", "Clive Barker", "Dean Koontz", "Joe Hill",
    "H. P. Lovecraft", "Paul Tremblay",
    # romance / YA
    "Nora Roberts", "Nicholas Sparks", "Colleen Hoover", "Jojo Moyes", "Julia Quinn",
    "Emily Henry", "Jasmine Guillory", "Suzanne Collins", "John Green", "Rick Riordan",
    "Cassandra Clare", "Leigh Bardugo", "Sarah J. Maas", "Veronica Roth", "Angie Thomas",
    "Holly Black",
    # classics
    "Jane Austen", "Charles Dickens", "Fyodor Dostoevsky", "Leo Tolstoy", "Mark Twain",
    "Ernest Hemingway", "F. Scott Fitzgerald", "Virginia Woolf", "George Orwell",
    "Franz Kafka", "Oscar Wilde", "Herman Melville", "Victor Hugo", "Charlotte Bronte",
    # nonfiction / science / business / history
    "Yuval Noah Harari", "Malcolm Gladwell", "Carl Sagan", "Richard Dawkins",
    "Stephen Hawking", "Bill Bryson", "Mary Roach", "Michio Kaku", "Brian Greene",
    "Daniel Kahneman", "Steven Pinker", "Jared Diamond", "Oliver Sacks", "James Clear",
    "Brene Brown", "Cal Newport", "Simon Sinek", "Robert Greene", "Dale Carnegie",
    "Stephen Covey", "Charles Duhigg", "Angela Duckworth", "Adam Grant",
    "Walter Isaacson", "Erik Larson", "David McCullough", "Ron Chernow", "Doris Kearns Goodwin",
]

# Free-text theme queries — surface books a strict subject taxonomy misses.
THEMES = [
    "artificial intelligence and society", "climate change and the future",
    "the history of money", "quantum physics explained", "consciousness and the brain",
    "world mythology and legends", "the philosophy of happiness", "ancient civilizations",
    "the science of sleep", "behavioral economics", "the future of work",
    "space exploration history", "genetics and DNA", "the psychology of persuasion",
    "minimalism and simple living", "strategy and the art of war", "renewable energy",
    "the gut microbiome", "stoic philosophy for modern life", "the history of art",
    "great scientific discoveries", "the power of habit", "emotional intelligence",
    "machine learning for beginners", "the history of philosophy", "evolution explained",
    "cold war espionage", "true crime investigations", "mountaineering survival stories",
    "deep ocean exploration", "the rise of empires", "lost ancient technologies",
    "the future of humanity", "pandemics and disease history", "the meaning of life",
    "money and investing for beginners", "productivity and deep work",
    "the science of happiness", "memory and how it works", "the history of language",
    "great explorers and adventurers", "women in science", "the human body explained",
    "philosophy of mind", "the universe and time", "creativity and innovation",
    "leadership and influence", "negotiation and decision making",
    "the psychology of money", "habits of successful people",
]
PAGE_SIZE = 40
PAGES_PER_SUBJECT = 25          # up to 1000 books per query
MIN_DESC_WORDS = 20            # quality floor for the NLP corpus
RATE_SLEEP = 0.1
TARGET_UNIQUE = 15000          # stop once the corpus reaches this many books


def _log(msg: str) -> None:
    print(msg, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _load_keys() -> list[tuple[str, str]]:
    names = ["GOOGLE_BOOKS_API_KEY"] + [f"GOOGLE_BOOKS_API_KEY_{i}" for i in range(2, 11)]
    return [(n, v) for n in names if (v := os.getenv(n, "").strip())]


def _build_queries() -> list[str]:
    """All query axes. New axes (MORE_SUBJECTS / AUTHORS / THEMES) go FIRST so a
    resumed run mines fresh books before re-touching the (already-drained,
    cheaply-skipped) original subjects + eval phrases."""
    queries: list[str] = []
    queries += [f'subject:"{g}"' for g in MORE_SUBJECTS]
    queries += [f'inauthor:"{a}"' for a in AUTHORS]
    queries += list(THEMES)
    queries += [f'subject:"{g}"' for g in SUBJECTS]
    tq = config.PROJECT_ROOT / "_team_repo" / "AI" / "data" / "eval" / "test_queries.json"
    if tq.exists():
        for item in json.loads(tq.read_text(encoding="utf-8")):
            if item.get("query"):
                queries.append(item["query"])
    # de-dup while preserving order (a theme could echo a subject phrase)
    seen: set[str] = set()
    return [q for q in queries if not (q in seen or seen.add(q))]


def _extract(vol: dict) -> dict:
    ids = vol.get("industryIdentifiers") or []
    isbn13 = next((i.get("identifier") for i in ids if i.get("type") == "ISBN_13"), None)
    isbn10 = next((i.get("identifier") for i in ids if i.get("type") == "ISBN_10"), None)
    img = (vol.get("imageLinks") or {}).get("thumbnail")
    year = re.match(r"(\d{4})", vol.get("publishedDate") or "")
    return {
        "isbn_13": isbn13,
        "isbn_10": isbn10,
        "title": vol.get("title") or "",
        "subtitle": vol.get("subtitle") or "",
        "authors": "|".join(vol.get("authors") or []),
        "description": _clean_html(vol.get("description", "") or ""),
        "categories": "|".join(vol.get("categories") or []),
        "average_rating": vol.get("averageRating"),
        "ratings_count": vol.get("ratingsCount"),
        "thumbnail": img.replace("http://", "https://") if img else None,
        "page_count": vol.get("pageCount"),
        "published_year": int(year.group(1)) if year else None,
        "language": vol.get("language"),
        "publisher": vol.get("publisher"),
    }


def _dedup_key(rec: dict) -> str:
    if rec["isbn_13"]:
        return f"isbn:{rec['isbn_13']}"
    a = rec["authors"].split("|")[0].lower().strip()
    return f"ta:{rec['title'].lower().strip()}|{a}"


def _keep(rec: dict) -> bool:
    if (rec.get("language") or "en") != "en":
        return False
    return len(rec["description"].split()) >= MIN_DESC_WORDS


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"done_pages": []}


def _load_seen() -> set[str]:
    seen: set[str] = set()
    if OUT_FILE.exists():
        with OUT_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    seen.add(_dedup_key(json.loads(line)))
    return seen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="1 subject, 2 pages, print only")
    args = ap.parse_args()

    keys = _load_keys()
    if not keys:
        _log("ERROR: no GOOGLE_BOOKS_API_KEY* in .env")
        sys.exit(1)
    session = _make_session()

    all_queries = _build_queries()
    queries = all_queries[:1] if args.test else all_queries
    pages = 2 if args.test else PAGES_PER_SUBJECT
    state = {"done_pages": []} if args.test else _load_state()
    done_pages = set(state["done_pages"])
    seen = set() if args.test else _load_seen()
    _log(f"{len(keys)} key(s) | {len(queries)} queries | already have {len(seen)} books, "
         f"{len(done_pages)} pages done | target {TARGET_UNIQUE}")
    if not args.test and len(seen) >= TARGET_UNIQUE:
        _log(f"already at target ({len(seen)} >= {TARGET_UNIQUE}); nothing to do.")
        return

    key_i = 0
    exhausted: set[int] = set()
    kept = pages_fetched = 0
    out = None if args.test else OUT_FILE.open("a", encoding="utf-8")
    try:
        for query in queries:
            dry = 0  # consecutive pages with no new (unseen) books
            for p in range(pages):
                start = p * PAGE_SIZE
                page_id = f"{query}:{start}"
                if page_id in done_pages:
                    continue
                # --- rotating GET ---
                data = None
                while data is None:
                    name, key = keys[key_i]
                    try:
                        data = _get_json(
                            config.GOOGLE_BOOKS_BASE, session,
                            params={
                                "q": query,
                                "startIndex": start, "maxResults": PAGE_SIZE,
                                "langRestrict": "en", "country": "US", "key": key,
                            },
                            raise_on_quota=True,
                        )
                        if data is None:  # transient failure exhausted retries
                            data = {"items": []}
                    except GoogleQuotaExceeded:
                        exhausted.add(key_i)
                        _log(f"key {name} exhausted ({len(exhausted)}/{len(keys)})")
                        nxt = next((j for j in range(len(keys)) if j not in exhausted), None)
                        if nxt is None:
                            _log(f"all keys exhausted; kept {kept} this run; resume tomorrow.")
                            return
                        key_i = nxt
                pages_fetched += 1
                time.sleep(RATE_SLEEP)

                items = data.get("items") or []
                if not items:
                    if not args.test:
                        done_pages.add(page_id)  # subject drained
                    break

                new_here = 0
                for it in items:
                    rec = _extract(it.get("volumeInfo", {}))
                    if not _keep(rec):
                        continue
                    k = _dedup_key(rec)
                    if k in seen:
                        continue
                    seen.add(k)
                    kept += 1
                    new_here += 1
                    if args.test:
                        _log(f"  + {rec['title'][:45]:<45} cats={rec['categories'][:30]!r} "
                             f"isbn={rec['isbn_13']} desc={len(rec['description'].split())}w")
                    else:
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        out.flush()

                if not args.test:
                    done_pages.add(page_id)
                    STATE_FILE.write_text(json.dumps({"done_pages": sorted(done_pages)}),
                                          encoding="utf-8")
                # stop paginating a query once it stops yielding unseen books
                dry = dry + 1 if new_here == 0 else 0
                if dry >= 2:
                    break
                if pages_fetched % 10 == 0:
                    _log(f"  [{query[:32]}] start={start} | +{new_here} new | total {len(seen)} "
                         f"| {pages_fetched} pages | key {keys[key_i][0]}")
                if not args.test and len(seen) >= TARGET_UNIQUE:
                    _log(f"reached target {TARGET_UNIQUE} (total {len(seen)}); stopping.")
                    return
    finally:
        if out:
            out.close()

    _log(f"DONE: kept {kept} new this run; total unique now {len(seen)}.")


if __name__ == "__main__":
    main()
