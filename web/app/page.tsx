import type { CSSProperties } from "react";
import { BipartiteStage } from "@/components/BipartiteStage";

function Arrow() {
  return (
    <svg className="m-arrow" viewBox="0 0 12 12" aria-hidden="true">
      <path className="m-arrow__stem" d="M1 6h8" />
      <path className="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5" />
    </svg>
  );
}

function Chevron() {
  return (
    <svg className="chev" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <>
      <header className="nav">
        <div className="wrap nav__bar">
          <a className="skip-link" href="#top">Skip to content</a>
          <a className="nav__logo" href="#top">
            <img src="/lollipop.png" alt="" width={40} height={40} />
            Lollipop
          </a>
          <nav className="nav__links" aria-label="Main">
            <div className="nav__item">
              <a className="nav__link" href="#search">
                Search <Chevron />
              </a>
              <div className="nav__menu">
                <div className="wrap grid">
                  <div className="menu-col span-3">
                    <p className="t-label">Programs</p>
                    <a href="#method">Peel a side<span>Drop vertices under a degree</span></a>
                    <a href="#method">Score a cell<span>Planted piece or exact solve</span></a>
                    <a href="#limit">Identity call<span>return peel(0, 0)</span></a>
                  </div>
                  <div className="menu-col span-3">
                    <p className="t-label">Graphs</p>
                    <a href="#search">Dev cuts<span>Orders 40 to 160 vertices</span></a>
                    <a href="#limit">Oracle cap<span>Stops past 250 vertices</span></a>
                    <a href="#questions">Three families<span>Wiktionary, Wikiquote, papers</span></a>
                  </div>
                  <a className="menu-card span-3 start-10" href="#search">
                    <div className="panel" role="img" aria-label="Two columns of a small bipartite graph">
                      <div className="stage stage--fade-br">
                        <svg className="at-corner" viewBox="0 0 160 120" width="160" height="120" aria-hidden="true">
                          <line x1="28" y1="24" x2="120" y2="28" stroke="#c2186a" strokeWidth="2" />
                          <line x1="28" y1="56" x2="120" y2="56" stroke="#c2186a" strokeWidth="2" />
                          <line x1="28" y1="88" x2="120" y2="84" stroke="#1a1216" strokeOpacity="0.35" />
                          <circle cx="28" cy="24" r="7" fill="#c2186a" />
                          <circle cx="28" cy="56" r="7" fill="#c2186a" />
                          <circle cx="28" cy="88" r="7" fill="#1a1216" />
                          <circle cx="120" cy="28" r="7" fill="#c2186a" />
                          <circle cx="120" cy="56" r="7" fill="#c2186a" />
                          <circle cx="120" cy="84" r="7" fill="#1a1216" />
                        </svg>
                      </div>
                    </div>
                    <span className="t-label">Graph</span>
                    One small peel
                    <span>Stepped in the browser</span>
                  </a>
                </div>
              </div>
            </div>
            <div className="nav__item"><a className="nav__link" href="#method">Method</a></div>
            <div className="nav__item"><a className="nav__link" href="#limit">Limit</a></div>
            <div className="nav__item"><a className="nav__link" href="#questions">Questions</a></div>
          </nav>
          <div className="nav__actions">
            <a className="btn btn--primary" href="#search">See the search<Arrow /></a>
          </div>
          <button className="nav__toggle" type="button" aria-expanded="false" aria-label="Menu">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path d="M2 5h14M2 13h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </header>

      <main id="top">
        <section className="hero hero--collage section section--hero bg-dots" data-enter aria-labelledby="hero-h">
          <div className="wrap">
            <div className="hero-text grid hero__grid">
              <div className="hero__text span-5">
                <h1 id="hero-h">Bipartite search for graph researchers</h1>
                <p className="hero__lead">
                  Lollipop writes short programs that discard vertices until a bipartite graph leaves a γ-quasi-biclique, then scores how much of a planted piece returns.
                </p>
                <div className="btn-row">
                  <a className="btn btn--primary" href="#search">See the search<Arrow /></a>
                  <a className="btn btn--secondary" href="#method">Read the method</a>
                </div>
                <p className="hero__proof">Dev graphs are cut at 40, 60, 80, 120 and 160 vertices.</p>
              </div>
              <div
                className="hero__art span-6 start-7"
                data-fx="grain-gradient"
                data-fx-seed="7"
                role="img"
                aria-label="A list of Lollipop calls, with the degree-threshold steps on a card"
              >
                <div className="ly-piece ly-piece--main" aria-hidden="true">
                  <div className="ui ui-panel ui-win" data-open="Listed" data-work="Scoring" data-done="Baseline">
                    <div className="ui-win__bar">
                      <span className="ui-dots" aria-hidden="true"><i /><i /><i /></span>
                      <span className="ui-win__crumb">Lollipop <i>/</i> <b>Calls</b></span>
                    </div>
                    <div className="ui-win__body">
                      <nav className="ui-win__side" aria-hidden="true">
                        <span className="ui-win__nav is-on">Calls</span>
                        <span className="ui-win__nav">Graphs</span>
                        <span className="ui-win__nav">Scores</span>
                        <span className="ui-win__label">Gamma</span>
                        <span className="ui-win__nav">1/1</span>
                        <span className="ui-win__nav">9/10</span>
                        <span className="ui-win__nav">8/10</span>
                        <span className="ui-win__nav">7/10</span>
                      </nav>
                      <div className="ui-win__main">
                        <div className="ui-win__cols" aria-hidden="true"><span /><span>Call</span><span>Detail</span><span>State</span></div>
                        <ul className="ui-win__rows">
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="1">Id</span><span className="ui-win__who">Identity</span><span className="ui-win__sub">return peel(0, 0)</span><span className="ui-win__st is-done">Baseline</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="2">Dg</span><span className="ui-win__who">Degree</span><span className="ui-win__sub">ceil(p * theta / q)</span><span className="ui-win__st is-done">Baseline</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="3">Mp</span><span className="ui-win__who">Map</span><span className="ui-win__sub">map(&quot;U&quot;, deg)</span><span className="ui-win__st">Listed</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="4">Pl</span><span className="ui-win__who">Peel</span><span className="ui-win__sub">peel(t, t)</span><span className="ui-win__st">Listed</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="5">Pt</span><span className="ui-win__who">Planted</span><span className="ui-win__sub">hidden dense piece</span><span className="ui-win__st">Scoring</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="1">Or</span><span className="ui-win__who">Oracle</span><span className="ui-win__sub">cap 250 vertices</span><span className="ui-win__st">Scoring</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="2">Ez</span><span className="ui-win__who">Too easy</span><span className="ui-win__sub">baseline at 0.99</span><span className="ui-win__st">Listed</span></li>
                          <li className="ui-win__row"><span className="ui-avatar" data-tone="3">Sd</span><span className="ui-win__who">Seed</span><span className="ui-win__sub">config seed 0</span><span className="ui-win__st">Listed</span></li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="ly-piece ly-piece--note note-card" aria-hidden="true" data-ly-steps="700">
                  <header>
                    <span>Degree threshold</span>
                    <span className="chip" data-step data-step-at="3">Extend</span>
                  </header>
                  <ol>
                    <li data-step><span>t = ceil(p × theta / q)</span></li>
                    <li data-step><span>Drop the largest deficit</span></li>
                    <li data-step><span>Extend the kept piece</span></li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="search" aria-labelledby="search-h">
          <div className="wrap">
            <div className="grid">
              <h2 className="span-5" id="search-h">The program and the kept piece</h2>
              <p className="span-6 start-7">
                A call peels one side, then the other. The list is the dev ladder. The graph is one small bipartite example, stepped in the browser. <a className="link" href="#method">Read the method</a>
              </p>
            </div>
            <div className="ui app fill" role="img" aria-label="Dev cuts beside a peel of one small bipartite graph" data-ui-pause-host>
              <div className="app__pane app__pane--list">
                <div className="ui ui-panel ui-win" data-open="Dev" data-work="Cell" data-done="Held">
                  <div className="ui-win__bar">
                    <span className="ui-dots" aria-hidden="true"><i /><i /><i /></span>
                    <span className="ui-win__crumb">Lollipop <i>/</i> <b>Dev cuts</b></span>
                  </div>
                  <div className="ui-win__body">
                    <nav className="ui-win__side" aria-hidden="true">
                      <span className="ui-win__nav is-on">Graphs</span>
                      <span className="ui-win__nav">Orders</span>
                      <span className="ui-win__nav">Cells</span>
                      <span className="ui-win__label">Families</span>
                      <span className="ui-win__nav">Wiktionary</span>
                      <span className="ui-win__nav">Wikiquote</span>
                      <span className="ui-win__nav">Papers</span>
                    </nav>
                    <div className="ui-win__main">
                      <div className="ui-win__cols" aria-hidden="true"><span /><span>Cut</span><span>Source</span><span>State</span><span> </span></div>
                      <ul className="ui-win__rows">
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="1">Wk</span><span className="ui-win__who">Wiktionary</span><span className="ui-win__sub">edit-zuwiktionary</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">40</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="2">Wq</span><span className="ui-win__who">Wikiquote</span><span className="ui-win__sub">edit-srwikiquote</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">60</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="3">Ap</span><span className="ui-win__who">Author-paper</span><span className="ui-win__sub">konect/matter</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">80</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="4">40</span><span className="ui-win__who">Order 40</span><span className="ui-win__sub">dev size</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">n</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="5">60</span><span className="ui-win__who">Order 60</span><span className="ui-win__sub">dev size</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">n</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="1">80</span><span className="ui-win__who">Order 80</span><span className="ui-win__sub">dev size</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">n</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="2">120</span><span className="ui-win__who">Order 120</span><span className="ui-win__sub">dev size</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">n</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="3">160</span><span className="ui-win__who">Order 160</span><span className="ui-win__sub">dev size</span><span className="ui-win__st" data-st>Dev</span><span className="ui-win__age">n</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="4">G1</span><span className="ui-win__who">Gamma 1/1</span><span className="ui-win__sub">theta 2 to 5</span><span className="ui-win__st" data-st>Cell</span><span className="ui-win__age">p/q</span></li>
                        <li className="ui-win__row" data-row><span className="ui-avatar" data-tone="5">G9</span><span className="ui-win__who">Gamma 9/10</span><span className="ui-win__sub">stage-one cell</span><span className="ui-win__st" data-st>Cell</span><span className="ui-win__age">p/q</span></li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              <div className="app__pane app__pane--open">
                <BipartiteStage />
              </div>
            </div>
          </div>
        </section>

        <section className="section ground-inverse" id="method" aria-labelledby="method-h">
          <div className="wrap">
            <div className="section-head">
              <h2 id="method-h">Score a program in 3 steps</h2>
            </div>
            <div className="grid">
              <article className="card card--row span-4">
                <span className="step-num">1</span>
                <h3>Discard low vertices</h3>
                <p>peel drops a vertex whose degree falls under the threshold on its side.</p>
                <div className="panel panel--flush" role="img" aria-label="A short reduce function that maps degree and calls peel">
                  <div className="stage stage--fade-b">
                    <div className="at-rise fit">
                      <div className="ui ui-panel ui-code" data-ui="code" data-ui-loop>
                        <div className="ui-code__tabs">
                          <span className="ui-code__tab is-on"><i className="ui-code__lang">PY</i>reduce.py</span>
                          <span className="ui-spacer" />
                          <span className="ui-chip ui-chip--plain ui-code__chip" data-code-chip>DSL</span>
                        </div>
                        <pre className="ui-code__pre"><code>
                          <span className="ui-code__ln" data-n="1"><span className="k">def</span> <span className="f">reduce</span>(G):</span>
                          <span className="ui-code__ln" data-n="2" data-note="Degree of every U vertex.">    du = <span className="f">map</span>(<span className="s">&quot;U&quot;</span>, deg)</span>
                          <span className="ui-code__ln" data-n="3" data-note="Integer threshold from p, theta and q.">    t = <span className="f">ceil</span>(p * theta / q)</span>
                          <span className="ui-code__ln is-mark" data-n="4">    <span className="k">return</span> <span className="f">peel</span>(t, t)</span>
                        </code></pre>
                        <div className="ui-code__hint" data-code-hint><span className="ui-dot" /><span data-code-text>Drop vertices under that degree.</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
              <article className="card card--row span-4">
                <span className="step-num">2</span>
                <h3>Score the planted piece</h3>
                <p>A hidden dense piece, or an exact solve under the vertex cap, is the mark.</p>
                <div className="panel panel--flush" role="img" aria-label="Four checks on a cell: planted piece, exact solve, too-easy cutoff, identity call">
                  <div className="stage stage--fade-b">
                    <div className="at-rise fit">
                      <div className="ui ui-panel ui-checks" data-ui="checklist">
                        <div className="ui-checks__head">
                          <div className="ui-title">Cell checks</div>
                          <span className="ui-spacer" />
                          <div className="ui-meta" data-checks-count>1 of 4</div>
                        </div>
                        <div className="ui-checks__bar"><i data-checks-bar style={{ "--k": "0.25" } as CSSProperties} /></div>
                        <ul className="ui-checks__list">
                          <li className="ui-check is-done"><span className="ui-check__box"><svg viewBox="0 0 16 16"><path d="m4.5 8.2 2.3 2.3 4.7-5" /></svg></span><span className="ui-check__label">Planted dense piece</span></li>
                          <li className="ui-check"><span className="ui-check__box"><svg viewBox="0 0 16 16"><path d="m4.5 8.2 2.3 2.3 4.7-5" /></svg></span><span className="ui-check__label">Exact solve at the cap</span></li>
                          <li className="ui-check"><span className="ui-check__box"><svg viewBox="0 0 16 16"><path d="m4.5 8.2 2.3 2.3 4.7-5" /></svg></span><span className="ui-check__label">Baseline at 0.99 leaves it</span></li>
                          <li className="ui-check"><span className="ui-check__box"><svg viewBox="0 0 16 16"><path d="m4.5 8.2 2.3 2.3 4.7-5" /></svg></span><span className="ui-check__label">Identity is peel(0, 0)</span></li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
              <article className="card card--row span-4">
                <span className="step-num">3</span>
                <h3>Keep work in proportion</h3>
                <p>The work has to stay in proportion to the graph as the edge count grows.</p>
                <div className="panel panel--flush" role="img" aria-label="Three keep rules: cost-ratio slope, rho kill, and work against size">
                  <div className="stage stage--fade-b">
                    <div className="at-rise fit">
                      <div className="ui ui-notify" data-ui="notify">
                        <ul className="ui-notify__list" data-notify-list>
                          <li className="ui-note"><span className="ui-note__ico"><svg className="ui-icon" viewBox="0 0 16 16"><path d="m3.5 8.4 2.8 2.8 6.2-6.4" /></svg></span><span className="ui-note__text"><span className="ui-note__title">Cost-ratio slope<time>kappa</time></span><span className="ui-note__body">Tested against log of the edge count</span></span></li>
                          <li className="ui-note"><span className="ui-note__ico"><svg className="ui-icon" viewBox="0 0 16 16"><path d="m3.5 8.4 2.8 2.8 6.2-6.4" /></svg></span><span className="ui-note__text"><span className="ui-note__title">Rho kill line<time>rho</time></span><span className="ui-note__body">A mean under the threshold scores 0</span></span></li>
                          <li className="ui-note"><span className="ui-note__ico"><svg className="ui-icon" viewBox="0 0 16 16"><path d="m3.5 8.4 2.8 2.8 6.2-6.4" /></svg></span><span className="ui-note__text"><span className="ui-note__title">Work and size<time>stage 2</time></span><span className="ui-note__body">Effort stays with the graph</span></span></li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="section" id="limit" data-moment="liquid-type" aria-labelledby="limit-h">
          <div className="wrap">
            <h2 className="mo-lt__type" id="limit-h">Checks stop at 250</h2>
            <p className="t-lead">The oracle stops once the two sides together pass 250 vertices. A larger graph is scored on the planted piece. A held-out graph stops at 3,000,000 simple edges, and the dev seed is 0.</p>
          </div>
        </section>

        <section className="section bg-mist" id="questions" aria-labelledby="questions-h">
          <div className="wrap">
            <div className="grid">
              <div className="span-4">
                <h2 id="questions-h">Questions</h2>
                <p>Limits of the ladder, in the words the runs use.</p>
                <a className="link" href="#method">Read the method</a>
              </div>
              <div className="faq span-8 start-5">
                <div className="faq__item">
                  <h3>How large is an exact check?</h3>
                  <p>The oracle stops once the two sides together pass 250 vertices. A larger graph is scored on the planted piece.</p>
                </div>
                <div className="faq__item">
                  <h3>Which graphs are in the dev set?</h3>
                  <p>Wiktionary, Wikiquote and author-paper, from the KONECT authorship graphs.</p>
                </div>
                <div className="faq__item">
                  <h3>What does the identity program return?</h3>
                  <p>peel(0, 0). That call deletes nothing.</p>
                </div>
                <div className="faq__item">
                  <h3>When is a cell left out?</h3>
                  <p>When the degree-threshold baseline already recovers 99% of the planted value. The cutoff is 0.99.</p>
                </div>
                <div className="faq__item">
                  <h3>Does this page run the scored search?</h3>
                  <p>The figure steps through one small bipartite graph in the browser. Scored runs use the dev cuts.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer closing footer--statement">
        <div className="wrap">
          <div className="closing__cta close--type">
            <div className="section-head">
              <h2 id="close-h">Watch one small graph get peeled</h2>
              <p className="t-small muted">Dev cuts stay on the KONECT graphs. This figure is drawn for the page.</p>
            </div>
            <a className="btn btn--primary btn--xl btn--wide" href="#search">
              See the search
              <Arrow />
            </a>
          </div>
          <div className="closing__links">
            <div className="grid">
              <div className="span-6 stack-5">
                <a className="footer__mark" href="#top">
                  <img src="/lollipop.png" alt="" width={40} height={40} />
                  Lollipop
                </a>
                <p className="footer__lede">Short programs for dense pieces of bipartite graphs.</p>
              </div>
              <div className="span-3 start-7 footer__col">
                <h3>Product</h3>
                <ul>
                  <li><a href="#search">Search</a></li>
                  <li><a href="#method">Method</a></li>
                  <li><a href="#limit">Limit</a></li>
                </ul>
              </div>
              <div className="span-3 footer__col">
                <h3>Page</h3>
                <ul>
                  <li><a href="#questions">Questions</a></li>
                  <li><a href="/privacy">Privacy</a></li>
                  <li><a href="/terms">Terms</a></li>
                </ul>
              </div>
            </div>
            <div className="footer__legal">
              <span>© 2026 Lollipop</span>
              <span><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></span>
            </div>
          </div>
        </div>
      </footer>

      <nav className="actionbar" aria-label="Quick actions">
        <a className="btn btn--primary" href="#search">See the search<Arrow /></a>
      </nav>
    </>
  );
}
