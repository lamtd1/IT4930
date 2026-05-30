// ============================================================
//  app.jsx — nav, hash router, theme, modal host
// ============================================================
import { useState as useStateA, useEffect as useEffectA } from 'react'
import { Icon, Popover, MethodsExplained } from './ui'
import { SearchPage } from './page_search'
import { CompareMethodsPage } from './page_compare'
import { EvaluationDashboard } from './page_eval'
import { BookDetailModal } from './modal'

const ROUTES = [
  { path: "/", label: "Search", icon: "search" },
  { path: "/compare", label: "Compare", icon: "compare" },
  { path: "/evaluation", label: "Evaluation", icon: "chart" },
];

function useHashRoute() {
  const get = () => { const h = (location.hash || "#/").replace(/^#/, ""); return h || "/"; };
  const [route, setRoute] = useStateA(get());
  useEffectA(() => {
    const h = () => { setRoute(get()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", h);
    if (!location.hash) location.hash = "#/";
    return () => window.removeEventListener("hashchange", h);
  }, []);
  return route;
}

function useTheme() {
  const [theme, setTheme] = useStateA(() => localStorage.getItem("sbr-theme") || "light");
  useEffectA(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sbr-theme", theme);
  }, [theme]);
  return [theme, () => setTheme(t => t === "light" ? "dark" : "light")];
}

function NavLink({ route, current }) {
  const active = current === route.path;
  return (
    <a href={"#" + route.path} style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "8px 13px",
      borderRadius: "var(--r-md)", fontSize: 13.5, fontWeight: 600, transition: "all .14s",
      color: active ? "var(--ink)" : "var(--ink-mute)", background: active ? "var(--paper-2)" : "transparent",
      position: "relative" }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.color = "var(--ink-soft)"; }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.color = "var(--ink-mute)"; }}>
      <Icon name={route.icon} size={16} stroke={active ? 2 : 1.7} />
      {route.label}
    </a>
  );
}

function NavBar({ current, theme, toggleTheme }) {
  return (
    <header style={{ position: "sticky", top: 0, zIndex: 50, background: "oklch(0.985 0.006 80 / 0.86)",
      backdropFilter: "saturate(1.4) blur(12px)", borderBottom: "1px solid var(--line)" }}>
      <style>{`[data-theme="dark"] header { background: oklch(0.205 0.008 70 / 0.86) !important; }`}</style>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <a href="#/" style={{ display: "flex", alignItems: "center", gap: 11, minWidth: 0 }}>
          <span style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent)", color: "#fff",
            display: "grid", placeItems: "center", flexShrink: 0, boxShadow: "var(--shadow-sm)" }}><Icon name="book" size={18} fill /></span>
          <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.05, minWidth: 0 }}>
            <span className="serif" style={{ fontSize: 16.5, fontWeight: 700, letterSpacing: "-0.01em", whiteSpace: "nowrap" }}>Semantic Shelf</span>
            <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".1em", whiteSpace: "nowrap" }}>Book Recommender</span>
          </span>
        </a>

        <nav style={{ display: "flex", alignItems: "center", gap: 4 }} className="main-nav">
          {ROUTES.map(r => <NavLink key={r.path} route={r} current={current} />)}
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Popover align="right" width={360} trigger={(open) => (
            <button title="Methods explained" style={{ display: "inline-flex", alignItems: "center", gap: 6, height: 36, padding: "0 12px",
              borderRadius: "var(--r-md)", border: "1px solid var(--line)", background: open ? "var(--paper-2)" : "var(--surface)",
              color: "var(--ink-soft)", cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "inherit" }}>
              <Icon name="info" size={16} /><span className="nav-hide-sm">Methods</span>
            </button>
          )}>
            <MethodsExplained />
          </Popover>
          <button onClick={toggleTheme} title="Toggle theme" aria-label="Toggle theme" style={{ width: 36, height: 36, borderRadius: "var(--r-md)",
            border: "1px solid var(--line)", background: "var(--surface)", color: "var(--ink-soft)", cursor: "pointer", display: "grid", placeItems: "center" }}>
            <Icon name={theme === "light" ? "moon" : "sun"} size={17} />
          </button>
        </div>
      </div>
      <nav className="mobile-nav" style={{ display: "none", borderTop: "1px solid var(--line)", padding: "8px 12px", gap: 4, justifyContent: "center" }}>
        {ROUTES.map(r => <NavLink key={r.path} route={r} current={current} />)}
      </nav>
      <style>{`
        @media (max-width: 620px){
          .main-nav { display: none !important; }
          .mobile-nav { display: flex !important; }
        }
        @media (max-width: 440px){ .nav-hide-sm { display: none; } }
      `}</style>
    </header>
  );
}

function App() {
  const route = useHashRoute();
  const [theme, toggleTheme] = useTheme();
  const [openBook, setOpenBook] = useStateA(null);

  let page;
  if (route.startsWith("/compare")) page = <CompareMethodsPage onOpenBook={setOpenBook} />;
  else if (route.startsWith("/evaluation")) page = <EvaluationDashboard onOpenBook={setOpenBook} />;
  else page = <SearchPage onOpenBook={setOpenBook} />;

  return (
    <>
      <NavBar current={route.startsWith("/compare") ? "/compare" : route.startsWith("/evaluation") ? "/evaluation" : "/"} theme={theme} toggleTheme={toggleTheme} />
      <main style={{ flex: 1 }}>{page}</main>
      <footer style={{ borderTop: "1px solid var(--line)", padding: "22px 24px", marginTop: "auto" }}>
        <div style={{ maxWidth: "var(--maxw)", margin: "0 auto", display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap",
          fontSize: 12, color: "var(--ink-mute)" }}>
          <span>Semantic Book Recommender · IT4142 · HUST</span>
          <span className="mono">Prototype · mock data · TF-IDF · BM25 · BGE-small + ChromaDB · Hybrid RRF · Reranking</span>
        </div>
      </footer>
      {openBook && <BookDetailModal result={openBook} onClose={() => setOpenBook(null)} />}
    </>
  );
}

export default App;
