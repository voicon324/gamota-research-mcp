import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, Check, ChevronDown, CircleHelp, Clipboard, ExternalLink, Eye, FileSearch, Fingerprint, FlaskConical, GitBranch, Menu, Search, ShieldCheck, Sparkles, Waypoints, X } from 'lucide-react';

type CaseId = 'R1' | 'R2';
type ReportIndexItem = { id: string; title: string; game: string; as_of: string; confidence: string; research_status: string; path: string };
type ReportIssue = {
  id: string; type: string; severity: string; description: string; related_claim_id?: string;
  evidence_ids?: string[]; unavailable_evidence_ids?: string[]; directions?: Record<string, 'UP'|'DOWN'>;
  resolution?: 'ABSTAIN'|'NOT_COMPARABLE'; comparability?: 'COMPARABLE'|'NOT_COMPARABLE';
  comparison_signature?: string; explanation?: string; reasons?: string[];
};
type PublishedReport = {
  schema_version: string;
  report: { id: string; title: string; game: string; as_of: string; status: string; research_run_id: string; research_status: string };
  scope: { question: string; decision_goal?: string; period?: unknown; markets: string[]; platforms: string[]; assumptions: string[] };
  summary: { verdict: string; confidence: string; directional_decision?: { outcome: 'ABSTAIN'|'NOT_COMPARABLE'; reason: string; issue_ids: string[] } };
  findings: { id: string; statement: string; type: string; confidence: string; evidence_ids: string[]; implication?: string; validation: string }[];
  recommendations: { id: string; text: string; confidence: string; evidence_ids: string[] }[];
  unknowns: ReportIssue[];
  metrics: { evidence_ids: string[]; metric: string; value: string | number; unit?: string; data_type: string; market?: string; period?: string; scope?: string }[];
  sources: { id: string; url: string; title?: string; publisher?: string; published_at?: string; accessed_at?: string; provenance_status?: string }[];
  evidence: { id: string; source_id: string; excerpt: string; locator?: string; retrieved_at?: string; metric?: string; value?: string | number; unit?: string; market?: string; period_start?: string; period_end?: string; scope?: string; method?: string; validation: string; claim_ids: string[] }[];
};
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
  const [mcpStatus, setMcpStatus] = useState<'idle'|'checking'|'online'|'error'>('idle');
  const [copied, setCopied] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [publishedReports, setPublishedReports] = useState<ReportIndexItem[]>([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportQuery, setReportQuery] = useState('');
  const [activeReport, setActiveReport] = useState<PublishedReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState('');
  const [expandedMetric, setExpandedMetric] = useState('');
  const [copiedFollowup, setCopiedFollowup] = useState('');
  const active = cases[caseId];

  useEffect(() => {
    fetch('/reports/index.json', { cache: 'no-store' })
      .then(async response => response.ok ? response.json() : { reports: [] })
      .then(data => setPublishedReports(Array.isArray(data.reports) ? data.reports : []))
      .catch(() => setPublishedReports([]))
      .finally(() => setReportsLoading(false));
  }, []);

  const visibleReports = useMemo(() => {
    const needle = reportQuery.trim().toLocaleLowerCase();
    return publishedReports.filter(item => !needle || `${item.game} ${item.title}`.toLocaleLowerCase().includes(needle));
  }, [publishedReports, reportQuery]);

  const openReport = useCallback(async (item: ReportIndexItem) => {
    setReportLoading(true);
    setReportError('');
    setActiveReport(null);
    setExpandedFinding('');
    try {
      const url = new URL(item.path, `${window.location.origin}/reports/index.json`);
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load report (${response.status})`);
      setActiveReport(await response.json());
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Could not load this report.');
    } finally {
      setReportLoading(false);
    }
  }, []);

  useEffect(() => {
    if (reportsLoading || publishedReports.length === 0) return;
    const reportId = new URLSearchParams(window.location.search).get('report');
    if (!reportId) return;
    const report = publishedReports.find(item => item.id === reportId);
    if (report) void openReport(report);
  }, [reportsLoading, publishedReports, openReport]);

  async function checkEndpoint() {
    setMcpStatus('checking');
    try {
      const response = await fetch('/mcp-public', {
        method: 'POST',
        headers: { Accept: 'application/json, text/event-stream', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0', id: 1, method: 'initialize',
          params: { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'fieldnotes-status-check', version: '1.0.0' } },
        }),
        cache: 'no-store',
      });
      const body = await response.text();
      setMcpStatus(response.ok && body.includes('protocolVersion') ? 'online' : 'error');
    } catch { setMcpStatus('error'); }
  }
  async function copyConfig() {
    await navigator.clipboard.writeText('[mcp_servers.gamota-research]\nurl = "https://52-64-163-35.sslip.io/mcp-public"');
    setCopied(true); window.setTimeout(() => setCopied(false), 1800);
  }
  async function copyResearchFollowup(issue: ReportIssue) {
    if (!activeReport) return;
    const evidenceContext = (issue.evidence_ids || []).map(id => {
      const evidence = activeReport.evidence.find(item => item.id === id);
      const source = evidence && activeReport.sources.find(item => item.id === evidence.source_id);
      return evidence ? `- ${id} (${issue.directions?.[id] || 'direction unavailable'}): ${evidence.excerpt}\n  Metric/scope: ${evidence.metric || 'unspecified'} · ${evidence.market || 'market unspecified'} · ${evidence.period_start || '?'} to ${evidence.period_end || '?'}\n  Source: ${source?.title || source?.url || 'source unavailable'}${source?.url ? ` — ${source.url}` : ''}` : `- ${id}: evidence unavailable in this report`;
    }).join('\n');
    const prompt = [
      'Continue the research in a new run. Keep the previous run and published report unchanged.',
      `Original question: ${activeReport.scope.question}`,
      `Previous research run ID: ${activeReport.report.research_run_id}`,
      `Market: ${activeReport.scope.markets.join(', ') || 'not specified'}`,
      `Platform: ${activeReport.scope.platforms.join(', ') || 'not specified'}`,
      `Period: ${activeReport.scope.period ? (typeof activeReport.scope.period === 'string' ? activeReport.scope.period : JSON.stringify(activeReport.scope.period)) : 'not specified'}`,
      `Issue: ${issue.type} (${issue.id}) — ${issue.description}`,
      `Resolution so far: ${issue.resolution || 'unresolved'}; ${issue.explanation || 'additional evidence is needed'}`,
      `Evidence IDs: ${(issue.evidence_ids || []).join(', ') || 'none'}`,
      'Existing evidence and sources:', evidenceContext || '- none',
      'Find new sources that measure the same market, metric, platform, and time period. Compare publication dates, methodology, and provenance. Record quotes and URLs. Do not invent data, assign an unsupported source-trust score, or choose a winner unless the new evidence justifies it.',
    ].join('\n');
    await navigator.clipboard.writeText(prompt);
    setCopiedFollowup(issue.id);
    window.setTimeout(() => setCopiedFollowup(current => current === issue.id ? '' : current), 1800);
  }

  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
      <a className="brand" href="#top" aria-label="Fieldnotes home"><span className="brand-mark"><Waypoints size={21}/></span><span>fieldnotes<small>GAMOTA RESEARCH</small></span></a>
      <div className="nav-caption">WORKSPACE</div>
      <nav className="side-nav">
        <a className="nav-item active" href="#published"><FileSearch size={17}/> Published reports <span className="nav-pip"/></a>
        <a className="nav-item" href="#research">Reference cases <small>R1 / R2</small></a>
        <a className="nav-item" href="#method"><GitBranch size={17}/> Method</a>
        <a className="nav-item" href="#connect"><FlaskConical size={17}/> Connect an agent</a>
      </nav>
      <div className="sidebar-foot"><span className="secure-icon"><ShieldCheck size={16}/></span><span><b>Research stays traceable</b><small>Claims link back to source evidence</small></span></div>
    </aside>

    <main id="top" className="main-view">
      <header className="topbar"><button className="mobile-menu" aria-label="Open menu" onClick={()=>setMenuOpen(!menuOpen)}>{menuOpen?<X size={20}/>:<Menu size={20}/>}</button><div className="crumb">Workspace <span>/</span> Research desk</div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={17}/></button><span className="top-divider"/><span className="agent-pill"><span/> HOST AGENT · CODEx / CLAUDE</span></div></header>
      <div className="content-wrap">
        <section className="hero">
          <div className="hero-copy"><div className="overline"><span className="live-mark"/> RESEARCH OPERATIONS <span className="overline-rule"/> MISSION 03 · A1</div><h1>Good research knows<br/>when to <em>stop.</em></h1><p>Let your AI agent search the web. Let evidence decide what the answer can claim.</p><div className="hero-actions"><a className="primary-button" href="#published"><Eye size={16}/> Browse published reports</a><a className="text-link" href="#method">How the checks work <ArrowDownRight size={15}/></a></div></div>
          <div className="hero-art" aria-label="Evidence lineage illustration"><div className="art-orbit orbit-a"/><div className="art-orbit orbit-b"/><svg className="lineage-lines" viewBox="0 0 360 260" aria-hidden="true"><path d="M62 72 C145 72 138 130 211 130 S267 70 312 70"/><path d="M62 188 C145 188 138 130 211 130 S267 190 312 190"/><path d="M62 72 C128 72 139 188 211 130"/></svg><div className="node node-a"><Fingerprint size={16}/><small>CLAIM</small></div><div className="node node-b"><FileSearch size={16}/><small>SOURCE</small></div><div className="node node-c"><Fingerprint size={15}/><small>CLAIM</small></div><div className="node node-root"><GitBranch size={17}/><small>ROOT</small></div><div className="art-label">Evidence lineage <span>01 claim · 03 documents · 01 origin</span></div><span className="art-coordinate">TRACE / 0081</span></div>
        </section>

        <section className="published-section" id="published">
          <div className="section-head"><div><div className="section-kicker">AGENT RESEARCH OUTPUT</div><h2>Published reports</h2></div><div className="section-tools"><span className="saved-indicator"><span/> {publishedReports.length} REPORT{publishedReports.length === 1 ? '' : 'S'}</span><label className="report-search"><Search size={15}/><input aria-label="Search published reports" value={reportQuery} onChange={event=>setReportQuery(event.target.value)} placeholder="Search games or reports"/></label></div></div>
          {reportsLoading ? <div className="reports-empty">Loading published reports…</div> : <div className={`published-layout ${activeReport ? 'has-report' : ''}`}>
            <div className="report-library-list">
              {visibleReports.length ? visibleReports.map(item=><button className={`report-library-card ${activeReport?.report.id===item.id?'selected':''}`} key={item.id} onClick={()=>openReport(item)}><span className="report-card-game">{item.game}</span><b>{item.title}</b><span className="report-card-meta">As of {item.as_of} · {item.confidence} confidence</span><span className="report-card-status">{item.research_status?.replaceAll('_',' ') || 'PUBLISHED'}</span></button>) : <div className="reports-empty">{reportQuery ? 'No reports match this search.' : 'No agent reports have been published yet. Ask Codex or Claude to research through the MCP, then call publish_game_decision_brief.'}</div>}
            </div>
            <div className="report-reader">
              {reportLoading ? <div className="reports-empty">Opening report…</div> : reportError ? <div className="reports-empty report-error">{reportError}</div> : activeReport ? <>
                <div className="reader-heading"><div className="section-kicker">GAME DECISION BRIEF · {activeReport.report.research_status}</div><h3>{activeReport.report.title}</h3><div className="reader-meta">{activeReport.report.game} · As of {activeReport.report.as_of} · {activeReport.summary.confidence} confidence</div></div>
                <div className="reader-question"><span>RESEARCH QUESTION</span><p>{activeReport.scope.question}</p><small>{[...activeReport.scope.markets, ...activeReport.scope.platforms].join(' · ') || 'Scope details in research contract'}{activeReport.scope.period ? ` · Period: ${typeof activeReport.scope.period === 'string' ? activeReport.scope.period : JSON.stringify(activeReport.scope.period)}` : ''}</small></div>
                {activeReport.summary.directional_decision&&<div className={`reader-directional ${activeReport.summary.directional_decision.outcome==='ABSTAIN'?'abstain':'not-comparable'}`}><span>SYSTEM DIRECTIONAL ASSESSMENT</span><strong>{activeReport.summary.directional_decision.outcome}</strong><p>{activeReport.summary.directional_decision.reason}</p><small>The executive verdict below is written by the publishing agent.</small></div>}
                <div className="reader-verdict"><span>EXECUTIVE VERDICT</span><p>{activeReport.summary.verdict}</p></div>
                <div className="reader-subhead"><h4>Market signals</h4><span>{activeReport.metrics.length}</span></div>
                {activeReport.metrics.length ? activeReport.metrics.map(metric=>{const metricKey=metric.evidence_ids.join(':');return <article className="metric-signal" key={metricKey}><button onClick={()=>setExpandedMetric(expandedMetric===metricKey?'':metricKey)}><span><b>{metric.metric.replaceAll('_',' ')}</b><strong>{metric.value} <small>{metric.unit}</small></strong><em>{metric.data_type} · {metric.market || 'market unspecified'}{metric.period?` · ${metric.period}`:''} · {metric.evidence_ids.length} evidence item{metric.evidence_ids.length===1?'':'s'}</em></span><ChevronDown size={16}/></button>{expandedMetric===metricKey&&metric.evidence_ids.map(id=>{const evidence=activeReport.evidence.find(item=>item.id===id);const source=evidence&&activeReport.sources.find(item=>item.id===evidence.source_id);return evidence?<div className="metric-evidence" key={id}><p>“{evidence.excerpt}”</p><small>{evidence.locator || 'Locator not specified'} · {evidence.validation}</small>{source&&<a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url} <ExternalLink size={12}/></a>}</div>:null})}</article>}):<p className="reader-muted">No scoped market signals were recorded.</p>}
                <div className="reader-subhead"><h4>Findings</h4><span>{activeReport.findings.length}</span></div>
                {activeReport.findings.map(finding=><article className="reader-finding" key={finding.id}><button className="finding-toggle" onClick={()=>setExpandedFinding(expandedFinding===finding.id?'':finding.id)}><span><i className={`finding-type ${finding.type}`}>{finding.type}</i><b>{finding.statement}</b><small>{finding.confidence} confidence · {finding.evidence_ids.length} evidence item{finding.evidence_ids.length===1?'':'s'}</small></span><ChevronDown size={17}/></button>{expandedFinding===finding.id&&<div className="finding-evidence">{finding.implication&&<p><b>Implication:</b> {finding.implication}</p>}{finding.evidence_ids.map(id=>{const item=activeReport.evidence.find(e=>e.id===id);const source=item&&activeReport.sources.find(s=>s.id===item.source_id);return item?<div className="evidence-item" key={id}><p>“{item.excerpt}”</p><small>{item.validation} · {item.locator || 'Locator not specified'}{item.retrieved_at?` · retrieved ${item.retrieved_at}`:''}</small>{source&&<a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url} <ExternalLink size={12}/></a>}</div>:null})}</div>}</article>)}
                <div className="reader-subhead"><h4>Recommended actions</h4><span>{activeReport.recommendations.length}</span></div>
                {activeReport.recommendations.length?activeReport.recommendations.map(item=><div className="reader-recommendation" key={item.id}><Sparkles size={15}/><span>{item.text}<small>{item.confidence} confidence · {item.evidence_ids.length} linked evidence items</small></span></div>):<p className="reader-muted">No evidence-linked recommendations were recorded.</p>}
                <div className="reader-subhead"><h4>Unknowns &amp; issues</h4><span>{activeReport.unknowns.length}</span></div>
                {activeReport.unknowns.length?activeReport.unknowns.map(item=>{
                  const linkedEvidence=(item.evidence_ids||[]).map(id=>({id,evidence:activeReport.evidence.find(e=>e.id===id)})).filter(row=>row.evidence);
                  const isDirectional=item.resolution==='ABSTAIN'||item.resolution==='NOT_COMPARABLE';
                  const reasons=item.reasons||[];
                  const unavailableEvidence=item.unavailable_evidence_ids||[];
                  return isDirectional?<article className={`conflict-card ${item.resolution==='ABSTAIN'?'is-abstain':'is-not-comparable'}`} key={item.id}>
                    <div className="conflict-card-head"><div><span className="conflict-kicker">{item.comparability||'SCOPE UNRESOLVED'} · {item.severity}</span><h5>{item.resolution==='ABSTAIN'?'Conflicting directions':'Observations are not comparable'}</h5></div><strong>{item.resolution}</strong></div>
                    <p className="conflict-description">{item.explanation||item.description}</p>
                    {reasons.length>0&&<div className="conflict-reasons">Comparison limits: {reasons.join(' · ')}</div>}
                    <div className="conflict-evidence-grid">{linkedEvidence.map(({id,evidence})=>{
                      const source=activeReport.sources.find(s=>s.id===evidence!.source_id);
                      const direction=item.directions?.[id];
                      return <section className={`conflict-evidence ${direction==='DOWN'?'is-down':direction==='UP'?'is-up':''}`} key={id}><div className="conflict-direction"><span>{direction||'DIRECTION UNKNOWN'}</span><small>{evidence!.metric?.replaceAll('_',' ')||'metric unspecified'} · {evidence!.market||'market unspecified'}</small></div><blockquote>“{evidence!.excerpt}”</blockquote><dl><div><dt>Period</dt><dd>{evidence!.period_start||'?'} – {evidence!.period_end||'?'}</dd></div><div><dt>Locator</dt><dd>{evidence!.locator||'Not specified'}</dd></div><div><dt>Published</dt><dd>{source?.published_at||'Date unknown'}</dd></div><div><dt>Provenance</dt><dd>{source?.provenance_status||'Unknown'}</dd></div></dl><small className="conflict-publisher">{source?.publisher||'Publisher unavailable'} · {evidence!.validation}</small>{source&&<a className="conflict-source-link" href={source.url} target="_blank" rel="noreferrer">{source.title||source.url}<ExternalLink size={13}/></a>}</section>;
                    })}</div>
                    {unavailableEvidence.length>0&&<div className="conflict-missing">Evidence not present in this report: {unavailableEvidence.join(', ')}</div>}
                    {item.resolution==='ABSTAIN'&&<button className="conflict-followup" onClick={()=>copyResearchFollowup(item)}><Clipboard size={14}/>{copiedFollowup===item.id?'Follow-up copied':'Copy contextual research follow-up'}</button>}
                  </article>:<div className="reader-unknown" key={item.id}><span>{item.severity}</span>{item.description}</div>;
                }):<p className="reader-muted">No open unknowns were recorded.</p>}
                <details className="reader-sources"><summary>Sources &amp; methodology · {activeReport.sources.length} sources</summary>{activeReport.sources.map(source=><a key={source.id} href={source.url} target="_blank" rel="noreferrer"><b>{source.title || source.url}</b><small>{source.publisher || 'Publisher unavailable'} · accessed {source.accessed_at || 'date unknown'}</small></a>)}{activeReport.scope.assumptions.length>0&&<ul>{activeReport.scope.assumptions.map(item=><li key={item}>{item}</li>)}</ul>}<p>Research performed by the host agent's native search/fetch tools. The MCP stores evidence and applies deterministic validation.</p><small>Run {activeReport.report.research_run_id} · schema {activeReport.schema_version}</small></details>
                <div className="reader-downloads"><a href={`/reports/${activeReport.report.id}/report.json`} download>Download JSON <ArrowDownRight size={13}/></a><a href={`/reports/${activeReport.report.id}/report.md`} download>Download Markdown <ArrowDownRight size={13}/></a></div>
              </> : <div className="reports-empty reader-placeholder"><FileSearch size={20}/><b>Select a published report</b><span>Findings can be expanded to inspect supporting evidence and source links.</span></div>}
            </div>
          </div>}
        </section>

        <details className="research-section reference-cases" id="research">
          <summary className="reference-summary"><span className="reference-copy"><span className="section-kicker">REFERENCE MATERIAL</span><b>Historical research cases</b><small>R1 and R2 are earlier examples, not reports published through MCP.</small></span><ChevronDown size={18}/></summary>
          <div className="reference-content">
          <div className="section-head"><div><div className="section-kicker">DECISION RECORD</div><h2>Research desk</h2></div><div className="section-tools"><span className="saved-indicator"><span/> 2 HISTORICAL CASES</span><button className="filter-button" onClick={()=>setShowTrace(!showTrace)}><GitBranch size={15}/>{showTrace?'Hide':'Show'} evidence trace <ChevronDown size={14}/></button></div></div>
          <div className="case-tabs" role="tablist" aria-label="Choose a research case"><button role="tab" aria-selected={caseId==='R2'} className={caseId==='R2'?'current':''} onClick={()=>setCaseId('R2')}><span className="tab-index">R2</span><span>Wuthering Waves<small>Hard case · conflicting scope</small></span><span className="tab-state warn-text">PARTIAL</span></button><button role="tab" aria-selected={caseId==='R1'} className={caseId==='R1'?'current':''} onClick={()=>setCaseId('R1')}><span className="tab-index">R1</span><span>Pokémon TCG Pocket<small>Positive case · bounded conclusion</small></span><span className="tab-state good-text">COMPLETE</span></button></div>
          <div className={`case-panel ${active.tone}`}>
            <div className="case-main"><div className="case-context"><span>{caseId} / REAL WEB RESEARCH</span><span className="case-date">{caseId==='R1'?'27 FEB 2025':'22 MAY — 20 JUN 2024'}</span></div><h3>{active.title}</h3><div className="case-subtitle">{active.subtitle}</div><div className="verdict-block"><div className="verdict-label"><span className="verdict-symbol">{caseId==='R1'?<Check size={14}/>:<CircleHelp size={14}/>}</span>{active.result}</div><div className="verdict-title">{active.verdict}</div><p>{active.detail}</p></div><div className="boundary-note"><span className="boundary-icon"><ShieldCheck size={17}/></span><span><b>Decision boundary</b><br/>{active.boundary}</span></div></div>
            <div className="case-side"><div className="side-top"><span>VALIDATION SNAPSHOT</span><span className="confidence-chip">CONFIDENCE · {active.confidence}</span></div><div className="metric-row"><span>Atomic claims</span><b>{active.claims}</b></div><div className="metric-row"><span>Required evidence slots</span><b>{active.slots}</b></div><div className="metric-row"><span>Source lineage</span><b>{active.sources}</b></div><div className="signal-chart"><div className="chart-head"><span>Evidence coverage</span><span>{caseId==='R1'?'COMPLETE':'GAP DETECTED'}</span></div><div className="chart-bars">{active.chart.map((h,i)=><i key={i} style={{height:`${h}%`}} className={caseId==='R2'&&i===11?'gap-bar':''}/>)}</div><div className="chart-axis"><span>Required scope</span><span>Observed sources</span></div></div></div>
          </div>
          {showTrace&&<div className="trace-panel"><div className="trace-head"><div><span className="section-kicker">CLAIM → EVIDENCE → SOURCE</span><h3>Follow the evidence</h3></div><span className={`trace-status ${active.tone}`}>{caseId==='R1'?'4 CLAIMS GROUNDED':'1 REQUIRED SLOT MISSING'}</span></div><div className="trace-body"><div className="claim-column"><span className="trace-column-title">RESEARCH CLAIM</span><div className="claim-card"><span className="claim-bullet"/><p>{caseId==='R1'?'The game passed 100M worldwide downloads within 120 days of global launch.':'Public evidence does not substantiate $100M mobile revenue during the first 30 launch days.'}</p><small>{caseId==='R1'?'VALID · bounded to global downloads':'PARTIAL · required metric/window unavailable'}</small></div><div className="lineage-caption"><span/> line shows recorded support, not independent corroboration</div></div><div className="trace-connector"><span/><span/><span/></div><div className="source-column"><span className="trace-column-title">SOURCE DOCUMENTS <b>{active.sources.split(' ')[0]}</b></span>{active.sourcesList.map((s,i)=><a className="source-row" href={s.href} target="_blank" rel="noreferrer" key={s.name}><span className={`source-num ${i===0?'primary':''}`}>{String(i+1).padStart(2,'0')}</span><span className="source-copy"><small>{s.type}</small><b>{s.name}</b><em>{s.note}</em></span><ExternalLink size={14}/></a>)}</div></div><div className={`origin-warning ${active.tone}`}><Fingerprint size={16}/><span><b>Lineage check</b> {active.flag}</span></div></div>}
          </div>
        </details>

        <section className="method-section" id="method"><div className="method-title"><div className="section-kicker">THE RESEARCH LOOP</div><h2>Your agent explores.<br/>The system checks.</h2><p>The host agent uses its native search and fetch tools. MCP preserves the audit trail and applies deterministic checks.</p><a className="text-link" href="https://github.com/voicon324/gamota-research-mcp" target="_blank" rel="noreferrer">Read the implementation <ExternalLink size={14}/></a></div><div className="loop-steps"><div className="loop-step"><span className="step-icon agent-step"><Search size={17}/></span><div><b>Agent researches</b><p>Codex or Claude searches with its own web tools and records URLs, quotes, and evidence.</p></div><span className="step-tag">HOST AGENT</span></div><div className="step-rule"/><div className="loop-step"><span className="step-icon mcp-step"><Clipboard size={17}/></span><div><b>MCP records &amp; publishes</b><p>Contracts, sources, claims, reports, and evidence persist with traceable links.</p></div><span className="step-tag">18 MCP TOOLS</span></div><div className="step-rule"/><div className="loop-step"><span className="step-icon check-step"><Activity size={17}/></span><div><b>Validator challenges</b><p>Grounding, freshness, metrics, scope, conflicts, and independent origins are checked.</p></div><span className="step-tag">DETERMINISTIC</span></div></div></section>

        <section className="connect-section" id="connect"><div><div className="section-kicker">READY FOR YOUR AGENT</div><h2>Bring the tools<br/>to your workflow.</h2><p>Connect the public MCP endpoint in ChatGPT, Codex, or Claude. Use the host agent’s own web search to research, then call Gamota Research to validate and publish the report.</p><div className="endpoint-line"><span className="endpoint-dot"/> https://52-64-163-35.sslip.io/mcp-public <button onClick={copyConfig} aria-label="Copy Codex configuration">{copied?<Check size={14}/>:<Clipboard size={14}/>} {copied?'COPIED':'COPY CONFIG'}</button></div><div className="disclaimer">No authentication. Anyone with this URL can read, create, change, or publish research. Use public information only.</div></div><div className="connect-card"><div className="connect-card-top"><span className="code-badge">&lt;/&gt;</span><div><b>Hosted MCP</b><small>Streamable HTTP · public access</small></div><span className={`status-live ${mcpStatus==='online'?'online':''}`}/></div><div className="connect-line"><span>Endpoint</span><code>/mcp-public</code></div><div className="connect-line"><span>Transport</span><code>Streamable HTTP</code></div><div className="connect-line"><span>Authentication</span><code>None</code></div><button className="check-button" onClick={checkEndpoint} disabled={mcpStatus==='checking'}>{mcpStatus==='checking'?'Checking endpoint…':mcpStatus==='online'?'MCP connected · check again':'Check MCP connection'} <ArrowUpRight size={15}/></button>{mcpStatus==='error'&&<div className="status-error">Could not initialize /mcp-public. The endpoint may be temporarily unavailable.</div>}{mcpStatus==='online'&&<div className="status-ok">Unauthenticated MCP initialize succeeded. Tools are ready to discover.</div>}</div></section>

        <footer className="footer"><a className="footer-brand" href="#top"><Waypoints size={17}/> Fieldnotes</a><span>Evidence-first research for mobile games</span><a href="https://github.com/voicon324/gamota-research-mcp" target="_blank" rel="noreferrer">Open source on GitHub <ExternalLink size={13}/></a></footer>
      </div>
    </main>
  </div>;
}
