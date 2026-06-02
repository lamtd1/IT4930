// ============================================================
//  data.jsx — mock corpus + simulated API (stands in for the
//  real backend: POST /search, GET /books/:isbn13, GET /stats,
//  GET /evaluation). Shapes match the spec exactly.
//
//  When VITE_API_BASE is set (see .env), apiSearch / apiBook hit
//  the real FastAPI backend; otherwise everything runs from the
//  mock corpus below so the UI is fully demoable offline.
// ============================================================

const API_BASE = import.meta.env.VITE_API_BASE;

const METHODS = [
  { id: "tfidf",     label: "TF-IDF + Cosine",      short: "TF-IDF",     type: "Sparse",        avgMs: 5,   color: "var(--m-tfidf)" },
  { id: "bm25",      label: "BM25",                 short: "BM25",      type: "Sparse",        avgMs: 10,  color: "var(--m-bm25)" },
  { id: "semantic",  label: "BGE-small + ChromaDB", short: "Semantic",  type: "Dense",         avgMs: 50,  color: "var(--m-semantic)" },
  { id: "hybrid",    label: "Hybrid RRF",           short: "Hybrid",    type: "Dense + Sparse", avgMs: 60,  color: "var(--m-hybrid)" },
  { id: "reranking", label: "BGE + Reranking",      short: "Reranking", type: "Dense + Rerank", avgMs: 200, color: "var(--m-reranking)" },
];
const METHOD_MAP = Object.fromEntries(METHODS.map(m => [m.id, m]));

const EMOTIONS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"];
const EMOTION_META = {
  joy:      { label: "Joy",      color: "oklch(0.80 0.085 85)" },
  sadness:  { label: "Sadness",  color: "oklch(0.62 0.068 250)" },
  anger:    { label: "Anger",    color: "oklch(0.60 0.105 28)" },
  fear:     { label: "Fear",     color: "oklch(0.56 0.072 300)" },
  surprise: { label: "Surprise", color: "oklch(0.71 0.092 55)" },
  disgust:  { label: "Disgust",  color: "oklch(0.63 0.075 135)" },
  neutral:  { label: "Neutral",  color: "oklch(0.70 0.012 70)" },
};

function emo(j, sa, an, fe, su, di, ne) {
  return { joy: j, sadness: sa, anger: an, fear: fe, surprise: su, disgust: di, neutral: ne };
}
function topEmotions(e) {
  return Object.entries(e).sort((a, b) => b[1] - a[1]).slice(0, 2).map(x => x[0]);
}
function cover(isbn) { return `https://covers.openlibrary.org/b/isbn/${isbn}-L.jpg`; }

// --- corpus ------------------------------------------------------------
const RAW_BOOKS = [
  { isbn13: "9780451524935", title: "1984", authors: "George Orwell", year: 1949,
    categories: "Fiction|Dystopian|Political", rating: 4.19, count: 4120000, cover: true,
    concepts: ["surveillance","totalitarianism","loss of freedom","paranoia","resistance","dystopia","government control"],
    e: emo(0.02,0.34,0.18,0.61,0.08,0.10,0.20),
    desc: "Winston Smith, a low-ranking member of the ruling Party in a future Britain, begins a forbidden diary and a doomed love affair under the constant gaze of Big Brother. A meditation on surveillance, language, and the machinery of total control." },

  { isbn13: "9780061120084", title: "To Kill a Mockingbird", authors: "Harper Lee", year: 1960,
    categories: "Fiction|Classic|Coming-of-Age", rating: 4.27, count: 5600000, cover: true,
    concepts: ["racial injustice","childhood","moral courage","small town","family","conscience","father daughter"],
    e: emo(0.30,0.40,0.22,0.18,0.10,0.06,0.24),
    desc: "Through the eyes of young Scout Finch in Depression-era Alabama, a lawyer father defends a Black man falsely accused of a crime. A tender, clear-eyed reckoning with prejudice, innocence, and quiet moral courage." },

  { isbn13: "9780307277671", title: "The Road", authors: "Cormac McCarthy", year: 2006,
    categories: "Fiction|Post-Apocalyptic|Literary", rating: 4.00, count: 980000, cover: true,
    concepts: ["father son","survival","grief","apocalypse","love","despair","journey","family secrets"],
    e: emo(0.04,0.58,0.10,0.55,0.05,0.12,0.16),
    desc: "A father and his young son walk alone through a burned, ashen America toward the coast, scavenging to stay alive and to keep a fragile flame of decency. A heartbreaking story about love, endurance, and what we owe the people we protect." },

  { isbn13: "9781594631931", title: "The Kite Runner", authors: "Khaled Hosseini", year: 2003,
    categories: "Fiction|Historical|Drama", rating: 4.34, count: 3100000, cover: true,
    concepts: ["betrayal","guilt","redemption","friendship","family secrets","afghanistan","childhood","atonement"],
    e: emo(0.10,0.52,0.20,0.30,0.12,0.10,0.18),
    desc: "In Kabul, the privileged Amir betrays his loyal friend Hassan, a wound that follows him across decades and continents. Years later a phone call offers a chance at atonement. A sweeping story of family secrets, guilt, and the long road to redemption." },

  { isbn13: "9780743273565", title: "The Great Gatsby", authors: "F. Scott Fitzgerald", year: 1925,
    categories: "Fiction|Classic|Literary", rating: 3.93, count: 4400000, cover: true,
    concepts: ["wealth","longing","lost love","the american dream","obsession","disillusion","jazz age"],
    e: emo(0.14,0.42,0.14,0.12,0.16,0.10,0.30),
    desc: "Narrator Nick Carraway is drawn into the glittering orbit of the mysterious millionaire Jay Gatsby, whose lavish parties mask an aching obsession with a lost love. A shimmering, melancholy portrait of longing and the hollow center of the American dream." },

  { isbn13: "9780385504201", title: "The Da Vinci Code", authors: "Dan Brown", year: 2003,
    categories: "Fiction|Mystery|Thriller", rating: 3.91, count: 2300000, cover: true,
    concepts: ["conspiracy","code breaking","secret society","murder","puzzle","religion","chase"],
    e: emo(0.08,0.06,0.14,0.40,0.34,0.06,0.24),
    desc: "A murder in the Louvre sends symbologist Robert Langdon on a frantic overnight hunt through ciphers, secret societies, and a hidden religious history. A breakneck puzzle-box thriller stacked with codes, twists, and chases." },

  { isbn13: "9780316769488", title: "The Catcher in the Rye", authors: "J. D. Salinger", year: 1951,
    categories: "Fiction|Classic|Coming-of-Age", rating: 3.80, count: 3300000, cover: true,
    concepts: ["alienation","teenage","grief","identity","loss of innocence","loneliness","rebellion"],
    e: emo(0.10,0.44,0.30,0.14,0.08,0.16,0.26),
    desc: "Over a few aimless winter days in New York, expelled teenager Holden Caulfield rails against a world he finds phony while grieving a loss he can barely name. A raw, funny, aching portrait of adolescent alienation." },

  { isbn13: "9780141439518", title: "Pride and Prejudice", authors: "Jane Austen", year: 1813,
    categories: "Fiction|Romance|Classic", rating: 4.28, count: 3900000, cover: true,
    concepts: ["romance","misunderstanding","family","wit","social class","marriage","slow burn"],
    e: emo(0.46,0.10,0.14,0.06,0.20,0.08,0.28),
    desc: "Spirited Elizabeth Bennet spars with the proud Mr. Darcy as five sisters navigate courtship, reputation, and money in Georgian England. A sparkling, sharp-witted romance about first impressions and second chances." },

  { isbn13: "9780618640157", title: "The Fellowship of the Ring", authors: "J. R. R. Tolkien", year: 1954,
    categories: "Fiction|Fantasy|Adventure", rating: 4.39, count: 2700000, cover: true,
    concepts: ["quest","good versus evil","friendship","journey","magic","sacrifice","epic"],
    e: emo(0.28,0.16,0.12,0.32,0.22,0.06,0.22),
    desc: "An unassuming hobbit inherits a ring of terrible power and sets out with an unlikely fellowship to destroy it before darkness swallows Middle-earth. The opening movement of a sweeping epic of friendship, courage, and sacrifice." },

  { isbn13: "9780307387899", title: "The Brief Wondrous Life of Oscar Wao", authors: "Junot Díaz", year: 2007,
    categories: "Fiction|Literary|Family Saga", rating: 3.96, count: 290000, cover: true,
    concepts: ["family curse","immigration","family secrets","love","identity","diaspora","tragedy"],
    e: emo(0.22,0.40,0.18,0.18,0.18,0.10,0.20),
    desc: "A sweet, doomed Dominican-American nerd in New Jersey dreams of love while a generational curse haunts his family across the brutal history of the Trujillo dictatorship. A dazzling, footnoted saga of family secrets and inheritance." },

  { isbn13: "9780743477154", title: "The Shining", authors: "Stephen King", year: 1977,
    categories: "Fiction|Horror|Thriller", rating: 4.25, count: 1300000, cover: true,
    concepts: ["haunting","isolation","family","madness","dread","father","supernatural"],
    e: emo(0.04,0.18,0.28,0.62,0.18,0.14,0.12),
    desc: "A struggling writer takes a winter caretaking job at an empty mountain hotel, bringing his wife and psychic son into its hungry, haunted halls. As the snow seals them in, the place works on his mind. A masterwork of mounting dread and family terror." },

  { isbn13: "9780525559474", title: "The Midnight Library", authors: "Matt Haig", year: 2020,
    categories: "Fiction|Fantasy|Contemporary", rating: 4.02, count: 1100000, cover: true,
    concepts: ["second chances","regret","depression","parallel lives","hope","meaning","choices"],
    e: emo(0.34,0.36,0.06,0.14,0.20,0.04,0.24),
    desc: "Between life and death sits a library where every book is a life Nora might have lived. Given the chance to undo her regrets, she tries on other versions of herself. A gentle, hopeful fable about despair, possibility, and learning to stay." },

  { isbn13: "9780374533557", title: "Thinking, Fast and Slow", authors: "Daniel Kahneman", year: 2011,
    categories: "Nonfiction|Psychology|Science", rating: 4.17, count: 520000, cover: true,
    concepts: ["cognitive bias","decision making","psychology","behavioral economics","reasoning","heuristics"],
    e: emo(0.12,0.04,0.04,0.06,0.30,0.04,0.60),
    desc: "A Nobel laureate maps the two systems that drive how we think: the fast, intuitive, error-prone one and the slow, deliberate one. A landmark tour of the biases that quietly steer our judgments and choices." },

  { isbn13: "9780062316097", title: "Sapiens: A Brief History of Humankind", authors: "Yuval Noah Harari", year: 2011,
    categories: "Nonfiction|History|Science", rating: 4.37, count: 980000, cover: true,
    concepts: ["human history","evolution","civilization","big ideas","anthropology","society"],
    e: emo(0.16,0.10,0.10,0.10,0.34,0.06,0.46),
    desc: "From foraging bands to global empires, this sweeping account argues that shared fictions—money, nations, religions—let humans cooperate at scale and remade the planet. A provocative, big-picture history of our species." },

  { isbn13: "9781400052189", title: "The Curious Incident of the Dog in the Night-Time", authors: "Mark Haddon", year: 2003,
    categories: "Fiction|Mystery|Contemporary", rating: 3.89, count: 1200000, cover: true,
    concepts: ["neurodivergence","mystery","family secrets","investigation","coming of age","father"],
    e: emo(0.18,0.30,0.16,0.30,0.26,0.06,0.22),
    desc: "Christopher, a fifteen-year-old who loves prime numbers and hates being touched, sets out to solve the killing of a neighbor's dog—and uncovers a far more painful truth about his own family. A singular mystery told in an unforgettable voice." },

  { isbn13: "9780399590504", title: "Educated", authors: "Tara Westover", year: 2018,
    categories: "Nonfiction|Memoir|Biography", rating: 4.47, count: 1500000, cover: true,
    concepts: ["family","education","escape","abuse","self invention","memory","estrangement"],
    e: emo(0.16,0.40,0.26,0.22,0.16,0.10,0.18),
    desc: "Raised by survivalist parents in rural Idaho, Tara Westover never set foot in a classroom until seventeen—then walked all the way to a Cambridge doctorate. A fierce memoir about family, loyalty, and the violence of self-invention." },

  { isbn13: "9780553386790", title: "A Game of Thrones", authors: "George R. R. Martin", year: 1996,
    categories: "Fiction|Fantasy|Epic", rating: 4.45, count: 2400000, cover: true,
    concepts: ["power","betrayal","family","war","politics","intrigue","epic","family secrets"],
    e: emo(0.10,0.24,0.30,0.34,0.22,0.10,0.16),
    desc: "As summer fades across the Seven Kingdoms, noble houses scheme for the Iron Throne while an ancient threat stirs beyond the Wall. A vast, ruthless saga of family, power, and betrayal where no one is safe." },

  { isbn13: "9780385537858", title: "The Goldfinch", authors: "Donna Tartt", year: 2013,
    categories: "Fiction|Literary|Coming-of-Age", rating: 3.91, count: 760000, cover: true,
    concepts: ["grief","art","loss of mother","obsession","coming of age","guilt","family"],
    e: emo(0.10,0.50,0.14,0.24,0.16,0.10,0.18),
    desc: "A bombing at a museum kills Theo's mother and leaves him clutching a small, priceless painting that will shape the rest of his life. A sprawling, Dickensian novel about grief, art, and the objects we cling to." },

  { isbn13: null, title: "Klara and the Sun", authors: "Kazuo Ishiguro", year: 2021,
    categories: "Fiction|Science Fiction|Literary", rating: 3.78, count: 540000, cover: false,
    concepts: ["artificial intelligence","love","loneliness","devotion","childhood illness","what it means to be human"],
    e: emo(0.24,0.40,0.04,0.16,0.18,0.04,0.34),
    desc: "Klara, an artificial friend with extraordinary powers of observation, watches the world from a store window and hopes to be chosen. When she is, she gives herself wholly to a fragile child. A quiet, devastating meditation on love and what it means to be human." },

  { isbn13: null, title: "Circe", authors: "Madeline Miller", year: 2018,
    categories: "Fiction|Fantasy|Mythology", rating: 4.27, count: 920000, cover: false,
    concepts: ["mythology","exile","transformation","power","womanhood","loneliness","gods"],
    e: emo(0.22,0.30,0.20,0.16,0.22,0.06,0.20),
    desc: "Banished to a deserted island, the witch Circe hones forbidden powers and crosses paths with gods, monsters, and mortals across the ages. A lush, feminist retelling of myth about exile, defiance, and becoming." },

  { isbn13: "9780316055437", title: "Gone Girl", authors: "Gillian Flynn", year: 2012,
    categories: "Fiction|Thriller|Mystery", rating: 4.10, count: 2900000, cover: true,
    concepts: ["marriage","deception","missing person","revenge","unreliable narrator","family secrets","twist"],
    e: emo(0.04,0.14,0.34,0.36,0.30,0.18,0.12),
    desc: "On their fifth anniversary, Amy Dunne vanishes and her husband Nick becomes the prime suspect. As the media circus swells, the story curdles into something far darker. A razor-sharp thriller about marriage, performance, and lies." },

  { isbn13: "9780743247542", title: "Angels & Demons", authors: "Dan Brown", year: 2000,
    categories: "Fiction|Thriller|Mystery", rating: 3.92, count: 1600000, cover: true,
    concepts: ["conspiracy","secret society","chase","science versus religion","murder","puzzle","race against time"],
    e: emo(0.06,0.08,0.16,0.42,0.32,0.06,0.22),
    desc: "Symbologist Robert Langdon races through Rome to stop an ancient brotherhood from destroying the Vatican with stolen antimatter. A high-velocity thriller of codes, catacombs, and a ticking clock." },
];

const BOOKS = RAW_BOOKS.map(b => {
  const e = b.e;
  return {
    isbn13: b.isbn13 || `INT-${b.title.replace(/\W+/g, "").slice(0, 10)}`,
    title: b.title,
    authors: b.authors,
    description: b.desc,
    categories: b.categories,
    thumbnail: b.cover && b.isbn13 ? cover(b.isbn13) : null,
    average_rating: b.rating,
    ratings_count: b.count,
    published_year: b.year,
    emotion_scores: e,
    top_emotions: topEmotions(e),
    _concepts: b.concepts,
    _text: (b.title + " " + b.authors + " " + b.categories.replace(/\|/g, " ") + " " + b.desc).toLowerCase(),
  };
});
const BOOK_BY_ISBN = Object.fromEntries(BOOKS.map(b => [b.isbn13, b]));

// --- query understanding (so methods diverge realistically) -----------
// Maps natural-language query words to the latent "concepts" books carry.
const CONCEPT_LEXICON = {
  "heartbreaking": ["grief","loss of mother","despair","tragedy","family secrets"],
  "heartbreak": ["grief","lost love","longing"],
  "family": ["family","family secrets","father son","father daughter","family saga","family curse"],
  "secrets": ["family secrets","betrayal","conspiracy","secret society"],
  "secret": ["family secrets","betrayal","conspiracy","secret society"],
  "love": ["romance","love","lost love","longing","devotion"],
  "romance": ["romance","slow burn","love","marriage"],
  "betrayal": ["betrayal","guilt","deception","revenge"],
  "revenge": ["revenge","betrayal","power"],
  "redemption": ["redemption","atonement","guilt","second chances"],
  "war": ["war","power","politics","conflict"],
  "power": ["power","politics","intrigue","totalitarianism"],
  "survival": ["survival","apocalypse","journey","endurance"],
  "apocalypse": ["apocalypse","post-apocalyptic","survival","despair"],
  "dystopia": ["dystopia","totalitarianism","surveillance","government control"],
  "dystopian": ["dystopia","totalitarianism","surveillance"],
  "surveillance": ["surveillance","government control","paranoia"],
  "coming": ["coming of age","childhood","loss of innocence","identity"],
  "age": ["coming of age","childhood","identity"],
  "growing": ["coming of age","childhood","identity"],
  "magic": ["magic","fantasy","quest"],
  "fantasy": ["magic","quest","mythology","epic"],
  "epic": ["epic","quest","war"],
  "mystery": ["mystery","investigation","puzzle","murder"],
  "murder": ["murder","investigation","mystery"],
  "thriller": ["chase","conspiracy","race against time","twist"],
  "conspiracy": ["conspiracy","secret society","code breaking"],
  "code": ["code breaking","puzzle","cipher"],
  "puzzle": ["puzzle","code breaking","investigation"],
  "ai": ["artificial intelligence","what it means to be human"],
  "robot": ["artificial intelligence","what it means to be human"],
  "intelligence": ["artificial intelligence"],
  "lonely": ["loneliness","alienation","isolation"],
  "loneliness": ["loneliness","alienation","isolation"],
  "isolation": ["isolation","loneliness","alienation"],
  "grief": ["grief","loss of mother","despair","loss"],
  "loss": ["grief","loss of mother","lost love","loss of innocence"],
  "guilt": ["guilt","atonement","redemption"],
  "hope": ["hope","second chances","meaning"],
  "regret": ["regret","second chances","choices"],
  "history": ["human history","historical","civilization"],
  "science": ["science","psychology","evolution"],
  "psychology": ["psychology","cognitive bias","decision making","reasoning"],
  "mind": ["psychology","cognitive bias","reasoning"],
  "myth": ["mythology","gods","transformation"],
  "mythology": ["mythology","gods","transformation"],
  "father": ["father son","father daughter","father","family"],
  "son": ["father son","family"],
  "marriage": ["marriage","romance","deception"],
  "horror": ["haunting","dread","supernatural","madness"],
  "haunted": ["haunting","supernatural","dread"],
  "scary": ["dread","fear","haunting"],
  "courage": ["moral courage","conscience","sacrifice"],
  "justice": ["racial injustice","conscience","moral courage"],
};

const STOPWORDS = new Set("a an the of and or to in on for with about that this is are was were be been story novel book books read tale".split(" "));

function tokenize(q) {
  return (q || "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(w => w && !STOPWORDS.has(w));
}
function expandConcepts(tokens) {
  const set = new Set();
  tokens.forEach(t => {
    (CONCEPT_LEXICON[t] || []).forEach(c => set.add(c));
    // singular/plural light stem
    if (t.endsWith("s")) (CONCEPT_LEXICON[t.slice(0, -1)] || []).forEach(c => set.add(c));
  });
  return set;
}

// scoring per method --------------------------------------------------
function lexicalScore(tokens, book) {
  // sparse keyword overlap against literal text — high precision, low recall
  let hits = 0;
  tokens.forEach(t => { if (t.length > 2 && book._text.includes(t)) hits++; });
  return tokens.length ? hits / tokens.length : 0;
}
function semanticScore(concepts, book) {
  if (!concepts.size) return 0;
  let inter = 0;
  book._concepts.forEach(c => { if (concepts.has(c)) inter++; });
  return inter / Math.sqrt(concepts.size * (book._concepts.length || 1));
}

function jitter(seed) { const x = Math.sin(seed) * 10000; return (x - Math.floor(x)); }

function rankBooks(query, method, emotionFilter) {
  const tokens = tokenize(query);
  const concepts = expandConcepts(tokens);
  let pool = BOOKS.slice();
  if (emotionFilter && emotionFilter.length) {
    pool = pool.filter(b => emotionFilter.some(em => b.emotion_scores[em] >= 0.28));
  }
  const scored = pool.map((b, i) => {
    const lex = lexicalScore(tokens, b);
    const sem = semanticScore(concepts, b);
    let s;
    if (method === "tfidf")        s = lex * 0.92 + jitter(i + 1) * 0.05;
    else if (method === "bm25")    s = lex * 1.0 + sem * 0.08 + jitter(i + 7) * 0.05;
    else if (method === "semantic")s = sem * 0.85 + lex * 0.12 + jitter(i + 3) * 0.04;
    else if (method === "hybrid")  s = sem * 0.55 + lex * 0.45 + jitter(i + 5) * 0.03;
    else /* reranking */           s = sem * 0.7 + lex * 0.15 + (b.average_rating / 5) * 0.15;
    return { book: b, raw: s };
  });
  scored.sort((a, b) => b.raw - a.raw);
  // normalise to plausible similarity scores (0.45–0.95 band)
  const max = scored[0]?.raw || 1;
  return scored.map((x, i) => {
    const norm = max > 0 ? x.raw / max : 0;
    const sim = +(0.45 + norm * 0.5 - i * 0.004).toFixed(3);
    return { ...x.book, similarity_score: Math.max(0.18, Math.min(0.98, sim)) };
  }).filter(x => x.similarity_score > 0.2);
}

// --- simulated network -------------------------------------------------
const wait = (ms) => new Promise(r => setTimeout(r, ms));

// global fault-injection switch for demoing error states
if (typeof window !== "undefined") {
  window.__API_FAULT = window.__API_FAULT || { search: false, evaluation: false, latency: 1 };
}
const fault = () => (typeof window !== "undefined" && window.__API_FAULT) || { search: false, evaluation: false, latency: 1 };

async function apiSearch({ query, top_k = 10, method = "semantic", filter_emotions = null }) {
  // Real backend (PRD §7) when configured.
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k, method, filter_emotions }),
    });
    if (!res.ok) { const e = new Error(`Search failed (${res.status})`); e.code = res.status; throw e; }
    return res.json();
  }
  const m = METHOD_MAP[method] || METHOD_MAP.semantic;
  await wait((420 + m.avgMs * 2.2) * (fault().latency || 1));
  if (fault().search) { const e = new Error("Search service unavailable (503)"); e.code = 503; throw e; }
  if (!query || !query.trim()) return { results: [], method_used: method, total_results: 0, query_time_ms: m.avgMs };
  let results = rankBooks(query, method, filter_emotions).slice(0, top_k);
  const t = +(m.avgMs * (0.8 + Math.random() * 0.5)).toFixed(1);
  return { results, method_used: method, total_results: results.length, query_time_ms: t };
}

async function apiBook(isbn13) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/books/${encodeURIComponent(isbn13)}`);
    if (!res.ok) { const e = new Error("Book not found (404)"); e.code = res.status; throw e; }
    return res.json();
  }
  await wait(280);
  const b = BOOK_BY_ISBN[isbn13];
  if (!b) { const e = new Error("Book not found (404)"); e.code = 404; throw e; }
  const { _concepts, _text, similarity_score, ...clean } = b;
  return clean;
}

async function apiStats() {
  await wait(300);
  const dist = {};
  EMOTIONS.forEach(em => { dist[em] = +(BOOKS.reduce((s, b) => s + b.emotion_scores[em], 0) / BOOKS.length).toFixed(3); });
  return { total_books: 6810, total_categories: 142, avg_rating: 4.11, emotion_distribution: dist };
}

// --- evaluation fixtures ----------------------------------------------
const EVAL_MODELS = [
  { method: "tfidf",     p_at_5: 0.42, p_at_10: 0.38, mrr: 0.51, ms_per_query: 5 },
  { method: "bm25",      p_at_5: 0.54, p_at_10: 0.49, mrr: 0.63, ms_per_query: 10 },
  { method: "semantic",  p_at_5: 0.71, p_at_10: 0.66, mrr: 0.79, ms_per_query: 50 },
  { method: "hybrid",    p_at_5: 0.78, p_at_10: 0.72, mrr: 0.84, ms_per_query: 60 },
  { method: "reranking", p_at_5: 0.85, p_at_10: 0.79, mrr: 0.90, ms_per_query: 200 },
];
const EVAL_GENRES = [
  { genre: "Literary",    scores: { tfidf: 0.38, bm25: 0.50, semantic: 0.74, hybrid: 0.80, reranking: 0.88 } },
  { genre: "Mystery",     scores: { tfidf: 0.49, bm25: 0.61, semantic: 0.69, hybrid: 0.76, reranking: 0.83 } },
  { genre: "Fantasy",     scores: { tfidf: 0.45, bm25: 0.57, semantic: 0.72, hybrid: 0.79, reranking: 0.86 } },
  { genre: "Romance",     scores: { tfidf: 0.40, bm25: 0.52, semantic: 0.70, hybrid: 0.77, reranking: 0.84 } },
  { genre: "Nonfiction",  scores: { tfidf: 0.47, bm25: 0.58, semantic: 0.66, hybrid: 0.74, reranking: 0.81 } },
  { genre: "Sci-Fi",      scores: { tfidf: 0.36, bm25: 0.48, semantic: 0.73, hybrid: 0.81, reranking: 0.87 } },
];
const VOCAB_DEMO = [
  { query: "a heartbreaking story about family secrets",
    tfidf_top1: BOOK_BY_ISBN["9780385504201"], semantic_top1: BOOK_BY_ISBN["9781594631931"] },
  { query: "what it means to be human in the age of machines",
    tfidf_top1: null, semantic_top1: BOOK_BY_ISBN["INT-KlaraandtheSun"] || BOOKS.find(b => b.title === "Klara and the Sun") },
  { query: "lonely person searching for meaning",
    tfidf_top1: BOOK_BY_ISBN["9780743273565"], semantic_top1: BOOK_BY_ISBN["9780525559474"] },
  { query: "fighting an oppressive government",
    tfidf_top1: null, semantic_top1: BOOK_BY_ISBN["9780451524935"] },
  { query: "grieving the death of a parent",
    tfidf_top1: BOOK_BY_ISBN["9780553386790"], semantic_top1: BOOK_BY_ISBN["9780385537858"] },
  { query: "a chilling tale that keeps you up at night",
    tfidf_top1: null, semantic_top1: BOOK_BY_ISBN["9780743477154"] },
];

async function apiEvaluation() {
  await wait(560 * (fault().latency || 1));
  if (fault().evaluation) { const e = new Error("Evaluation data unavailable (500)"); e.code = 500; throw e; }
  return { models: EVAL_MODELS, by_genre: EVAL_GENRES, vocabulary_mismatch_demo: VOCAB_DEMO };
}

// preset example queries for the search page
const EXAMPLE_QUERIES = [
  "a heartbreaking story about family secrets",
  "lonely person searching for meaning",
  "what it means to be human in the age of machines",
  "fighting an oppressive government",
  "a chilling tale that keeps you up at night",
  "slow-burn romance with sharp banter",
];

export {
  METHODS, METHOD_MAP, EMOTIONS, EMOTION_META, BOOKS, BOOK_BY_ISBN,
  EXAMPLE_QUERIES, apiSearch, apiBook, apiStats, apiEvaluation,
  EVAL_MODELS, EVAL_GENRES, VOCAB_DEMO,
};
