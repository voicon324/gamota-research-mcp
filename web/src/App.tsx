import { useState } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, Check, ChevronDown, CircleHelp, Clipboard, ExternalLink, Eye, FileSearch, Fingerprint, FlaskConical, GitBranch, Menu, Search, ShieldCheck, Sparkles, Waypoints, X } from 'lucide-react';

type CaseId = 'R1' | 'R2';
const cases = {
  R1: {
    title: 'Pokémon TCG Pocket', subtitle: 'Global downloads · first 120 days', result: 'SUPPORTED, WITH LIMITS', tone: 'good',
    verdict: '100M+ worldwide downloads by day 120',
    detail: 'DeNA reports the milestone on Feb 27, 2025. From the Oct 30, 2024 global launch, that is 120 elapsed days.',
    boundary: 'A global traction signal for a deeper TCG teardown. It does not establish Vietnam demand, revenue, retention, or profitability.',
    claims: '4 / 4 valid', slots: '5 / 5 covered', sources: '3 sources · 2 roots', confidence: 'WEAK',
    sourcesList: [
      { type: 'PRIMARY · TIER A', name: 'DeNA · Global launch', note: 'Oct 30, 2024 · confirms launch date', href: 'https://dena.com/intl/news/4743/' },
      { type: 'PRIMARY · TIER A', name: 'DeNA · 100M downloads', note: 'Feb 27, 2025 · confirms milestone', href: 'https://dena.com/intl/news/4752/' },
      { type: 'TRADE PRESS · TIER B', name: 'PocketGamer.biz', note: 'Relays DeNA · not independent measurement', href: 'https://www.pocketgamer.biz/pokmon-tcg-pocket-surpasses-100-million-downloads/' },
    ],
    flag: 'Two primary documents share DeNA as their origin. The validator lowers confidence even though the claims are grounded.',
    chart: [68, 81, 54, 91, 73, 97, 85, 100, 69, 94, 78, 88],
  },
  R2: {
    title: 'Wuthering Waves', subtitle: 'Mobile revenue · first 30 launch days', result: 'NOT SUBSTANTIATED', tone: 'warn',
    verdict: 'The $100M threshold cannot be verified',
    detail: 'Reviewed figures measure a June calendar month, combined PC + mobile, or a later cumulative milestone. None matches the required mobile-only 30-day window.',
    boundary: 'Keep the required slot open. Do not backdate later totals, combine platforms, or treat gross and net estimates as equivalent.',
    claims: '7 / 7 valid', slots: '6 / 7 covered', sources: '4 sources · shared origin', confidence: 'WEAK',
    sourcesList: [
      { type: 'TRADE PRESS · APPMAGIC', name: 'PocketGamer.biz · later milestone', note: 'Cumulative mobile gross · later period', href: 'https://www.pocketgamer.biz/wuthering-waves-sails-past-100-million-in-under-two-months/' },
      { type: 'INDUSTRY ESTIMATE', name: 'GameDev Reports · June digest', note: 'Calendar-month net estimate · wrong window', href: 'https://gamedevreports.substack.com/p/appmagic-top-mobile-games-by-revenue-66e' },
      { type: 'RELAYED ESTIMATE', name: 'Game World Observer · launch coverage', note: 'Combined PC + mobile · wrong platform scope', href: 'https://gameworldobserver.com/2024/06/17/wuthering-waves-110-million-revenue-pc-and-mobile' },
    ],
    flag: 'One required evidence slot is missing. The validator records a blocking GAP and stops at PARTIAL / WEAK instead of guessing.',
    chart: [96, 85, 72, 62, 79, 54, 88, 44, 71, 58, 35, 49],
  },
};

export default function App() {
  const [caseId, setCaseId] = useState<CaseId>('R2');
  const [showTrace, setShowTrace] = useState(true);
  const [mcpStatus, setMcpStatus] = useState<'idle'|'checking'|'protected'|'error'>('idle');
  const [copied, setCopied] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const active = cases[caseId];

  async function checkEndpoint() {
    setMcpStatus('checking');
    try {
      const response = await fetch('/mcp', { method: 'GET', headers: { Accept: 'application/json' }, cache: 'no-store' });
      setMcpStatus(response.status === 401 ? 'protected' : 'error');
    } catch { setMcpStatus('error'); }
  }
  async function copyConfig() {
    await navigator.clipboard.writeText('[mcp_servers.gamota-research]\nurl = "https://52.64.163.35/mcp"\nheaders = { Authorization = "Bearer <YOUR_TOKEN>" }');
    setCopied(true); window.setTimeout(() => setCopied(false), 1800);
  }

  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
      <a className="brand" href="#top" aria-label="Fieldnotes home"><span className="brand-mark"><Waypoints size={21}/></span><span>fieldnotes<small>GAMOTA RESEARCH</small></span></a>
      <div className="nav-caption">WORKSPACE</div>
      <nav className="side-nav">
        <a className="nav-item active" href="#research"><FileSearch size={17}/> Research desk <span className="nav-pip"/></a>
        <a className="nav-item" href="#method"><GitBranch size={17}/> Method</a>
        <a className="nav-item" href="#connect"><FlaskConical size={17}/> Connect an agent</a>
      </nav>
      <div className="nav-caption recent-label">SAVED TRIALS</div>
      <button className={`saved-run ${caseId==='R1'?'selected':''}`} onClick={()=>{setCaseId('R1');setMenuOpen(false)}}><span className="run-dot positive"/><span><b>R1 · Pokémon TCG Pocket</b><small>SUPPORTED · WEAK</small></span></button>
      <button className={`saved-run ${caseId==='R2'?'selected':''}`} onClick={()=>{setCaseId('R2');setMenuOpen(false)}}><span className="run-dot warning"/><span><b>R2 · Wuthering Waves</b><small>PARTIAL · WEAK</small></span></button>
      <div className="sidebar-foot"><span className="secure-icon"><ShieldCheck size={16}/></span><span><b>Research stays traceable</b><small>Claims link back to source evidence</small></span></div>
    </aside>

    <main id="top" className="main-view">
      <header className="topbar"><button className="mobile-menu" aria-label="Open menu" onClick={()=>setMenuOpen(!menuOpen)}>{menuOpen?<X size={20}/>:<Menu size={20}/>}</button><div className="crumb">Workspace <span>/</span> Research desk</div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={17}/></button><span className="top-divider"/><span className="agent-pill"><span/> HOST AGENT · CODEx / CLAUDE</span></div></header>
      <div className="content-wrap">
        <section className="hero">
          <div className="hero-copy"><div className="overline"><span className="live-mark"/> RESEARCH OPERATIONS <span className="overline-rule"/> MISSION 02</div><h1>Good research knows<br/>when to <em>stop.</em></h1><p>Let your AI agent search the web. Let evidence decide what the answer can claim.</p><div className="hero-actions"><a className="primary-button" href="#research"><Eye size={16}/> Explore a real research run</a><a className="text-link" href="#method">How the checks work <ArrowDownRight size={15}/></a></div></div>
          <div className="hero-art" aria-label="Evidence lineage illustration"><div className="art-orbit orbit-a"/><div className="art-orbit orbit-b"/><svg className="lineage-lines" viewBox="0 0 360 260" aria-hidden="true"><path d="M62 72 C145 72 138 130 211 130 S267 70 312 70"/><path d="M62 188 C145 188 138 130 211 130 S267 190 312 190"/><path d="M62 72 C128 72 139 188 211 130"/></svg><div className="node node-a"><Fingerprint size={16}/><small>CLAIM</small></div><div className="node node-b"><FileSearch size={16}/><small>SOURCE</small></div><div className="node node-c"><Fingerprint size={15}/><small>CLAIM</small></div><div className="node node-root"><GitBranch size={17}/><small>ROOT</small></div><div className="art-label">Evidence lineage <span>01 claim · 03 documents · 01 origin</span></div><span className="art-coordinate">TRACE / 0081</span></div>
        </section>

        <section className="research-section" id="research">
          <div className="section-head"><div><div className="section-kicker">DECISION RECORD</div><h2>Research desk</h2></div><div className="section-tools"><span className="saved-indicator"><span/> 2 REAL-WEB TRIALS</span><button className="filter-button" onClick={()=>setShowTrace(!showTrace)}><GitBranch size={15}/>{showTrace?'Hide':'Show'} evidence trace <ChevronDown size={14}/></button></div></div>
          <div className="case-tabs" role="tablist" aria-label="Choose a research case"><button role="tab" aria-selected={caseId==='R2'} className={caseId==='R2'?'current':''} onClick={()=>setCaseId('R2')}><span className="tab-index">R2</span><span>Wuthering Waves<small>Hard case · conflicting scope</small></span><span className="tab-state warn-text">PARTIAL</span></button><button role="tab" aria-selected={caseId==='R1'} className={caseId==='R1'?'current':''} onClick={()=>setCaseId('R1')}><span className="tab-index">R1</span><span>Pokémon TCG Pocket<small>Positive case · bounded conclusion</small></span><span className="tab-state good-text">COMPLETE</span></button></div>
          <div className={`case-panel ${active.tone}`}>
            <div className="case-main"><div className="case-context"><span>{caseId} / REAL WEB RESEARCH</span><span className="case-date">{caseId==='R1'?'27 FEB 2025':'22 MAY — 20 JUN 2024'}</span></div><h3>{active.title}</h3><div className="case-subtitle">{active.subtitle}</div><div className="verdict-block"><div className="verdict-label"><span className="verdict-symbol">{caseId==='R1'?<Check size={14}/>:<CircleHelp size={14}/>}</span>{active.result}</div><div className="verdict-title">{active.verdict}</div><p>{active.detail}</p></div><div className="boundary-note"><span className="boundary-icon"><ShieldCheck size={17}/></span><span><b>Decision boundary</b><br/>{active.boundary}</span></div></div>
            <div className="case-side"><div className="side-top"><span>VALIDATION SNAPSHOT</span><span className="confidence-chip">CONFIDENCE · {active.confidence}</span></div><div className="metric-row"><span>Atomic claims</span><b>{active.claims}</b></div><div className="metric-row"><span>Required evidence slots</span><b>{active.slots}</b></div><div className="metric-row"><span>Source lineage</span><b>{active.sources}</b></div><div className="signal-chart"><div className="chart-head"><span>Evidence coverage</span><span>{caseId==='R1'?'COMPLETE':'GAP DETECTED'}</span></div><div className="chart-bars">{active.chart.map((h,i)=><i key={i} style={{height:`${h}%`}} className={caseId==='R2'&&i===11?'gap-bar':''}/>)}</div><div className="chart-axis"><span>Required scope</span><span>Observed sources</span></div></div></div>
          </div>
          {showTrace&&<div className="trace-panel"><div className="trace-head"><div><span className="section-kicker">CLAIM → EVIDENCE → SOURCE</span><h3>Follow the evidence</h3></div><span className={`trace-status ${active.tone}`}>{caseId==='R1'?'4 CLAIMS GROUNDED':'1 REQUIRED SLOT MISSING'}</span></div><div className="trace-body"><div className="claim-column"><span className="trace-column-title">RESEARCH CLAIM</span><div className="claim-card"><span className="claim-bullet"/><p>{caseId==='R1'?'The game passed 100M worldwide downloads within 120 days of global launch.':'Public evidence does not substantiate $100M mobile revenue during the first 30 launch days.'}</p><small>{caseId==='R1'?'VALID · bounded to global downloads':'PARTIAL · required metric/window unavailable'}</small></div><div className="lineage-caption"><span/> line shows recorded support, not independent corroboration</div></div><div className="trace-connector"><span/><span/><span/></div><div className="source-column"><span className="trace-column-title">SOURCE DOCUMENTS <b>{active.sources.split(' ')[0]}</b></span>{active.sourcesList.map((s,i)=><a className="source-row" href={s.href} target="_blank" rel="noreferrer" key={s.name}><span className={`source-num ${i===0?'primary':''}`}>{String(i+1).padStart(2,'0')}</span><span className="source-copy"><small>{s.type}</small><b>{s.name}</b><em>{s.note}</em></span><ExternalLink size={14}/></a>)}</div></div><div className={`origin-warning ${active.tone}`}><Fingerprint size={16}/><span><b>Lineage check</b> {active.flag}</span></div></div>}
        </section>

        <section className="method-section" id="method"><div className="method-title"><div className="section-kicker">THE RESEARCH LOOP</div><h2>Your agent explores.<br/>The system checks.</h2><p>The host agent uses its native search and fetch tools. MCP preserves the audit trail and applies deterministic checks.</p><a className="text-link" href="https://github.com/voicon324/gamota-research-mcp" target="_blank" rel="noreferrer">Read the implementation <ExternalLink size={14}/></a></div><div className="loop-steps"><div className="loop-step"><span className="step-icon agent-step"><Search size={17}/></span><div><b>Agent researches</b><p>Codex or Claude searches with its own web tools and records URLs, quotes, and evidence.</p></div><span className="step-tag">HOST AGENT</span></div><div className="step-rule"/><div className="loop-step"><span className="step-icon mcp-step"><Clipboard size={17}/></span><div><b>MCP records</b><p>Contracts, sources, claims, budgets, and progress persist in SQLite with traceable links.</p></div><span className="step-tag">15 MCP TOOLS</span></div><div className="step-rule"/><div className="loop-step"><span className="step-icon check-step"><Activity size={17}/></span><div><b>Validator challenges</b><p>Grounding, freshness, metrics, scope, conflicts, and independent origins are checked.</p></div><span className="step-tag">DETERMINISTIC</span></div></div></section>

        <section className="connect-section" id="connect"><div><div className="section-kicker">READY FOR YOUR AGENT</div><h2>Bring the tools<br/>to your workflow.</h2><p>Connect the hosted MCP endpoint in Codex or Claude. The web UI never needs the bearer token.</p><div className="endpoint-line"><span className="endpoint-dot"/> https://52.64.163.35/mcp <button onClick={copyConfig} aria-label="Copy Codex configuration">{copied?<Check size={14}/>:<Clipboard size={14}/>} {copied?'COPIED':'COPY CONFIG'}</button></div><div className="disclaimer">A bearer token is required. Deliver it to reviewers only through an approved private channel.</div></div><div className="connect-card"><div className="connect-card-top"><span className="code-badge">&lt;/&gt;</span><div><b>Hosted MCP</b><small>Streamable HTTP · bearer protected</small></div><span className={`status-live ${mcpStatus==='protected'?'online':''}`}/></div><div className="connect-line"><span>Endpoint</span><code>/mcp</code></div><div className="connect-line"><span>Transport</span><code>Streamable HTTP</code></div><div className="connect-line"><span>Authentication</span><code>Bearer token</code></div><button className="check-button" onClick={checkEndpoint} disabled={mcpStatus==='checking'}>{mcpStatus==='checking'?'Checking endpoint…':mcpStatus==='protected'?'Endpoint protected · check again':'Check endpoint status'} <ArrowUpRight size={15}/></button>{mcpStatus==='error'&&<div className="status-error">Could not reach /mcp from this browser. The site may still load normally.</div>}{mcpStatus==='protected'&&<div className="status-ok">Unauthenticated request received 401. The protected endpoint is responding.</div>}</div></section>

        <footer className="footer"><a className="footer-brand" href="#top"><Waypoints size={17}/> Fieldnotes</a><span>Evidence-first research for mobile games</span><a href="https://github.com/voicon324/gamota-research-mcp" target="_blank" rel="noreferrer">Open source on GitHub <ExternalLink size={13}/></a></footer>
      </div>
    </main>
  </div>;
}
