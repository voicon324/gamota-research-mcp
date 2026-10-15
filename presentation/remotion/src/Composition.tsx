import React from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type Props = {};
const FPS = 30;
const DURATION = 2400;
const BG = "#07111f";
const PANEL = "#101e30";
const CYAN = "#63e6d8";
const WHITE = "#f4f7fb";
const MUTED = "#91a2b8";

const calculateMetadata: CalculateMetadataFunction<Props> = () => ({
  durationInFrames: DURATION,
  fps: FPS,
  width: 1280,
  height: 720,
});

export const MyComposition = () => (
  <Composition id="GamotaMission2" component={MyComponent} durationInFrames={DURATION} fps={FPS} width={1280} height={720} calculateMetadata={calculateMetadata} />
);

const DotGrid: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, opacity: 0.18, backgroundImage: "radial-gradient(#7890aa 1px, transparent 1px)", backgroundSize: "28px 28px" }} />
);

const Frame: React.FC<{ n: string; label: string; children: React.ReactNode }> = ({ n, label, children }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(f, [0, 18, 420, 450], [0, 1, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const lift = interpolate(f, [0, 22], [28, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
  return (
    <AbsoluteFill style={{ backgroundColor: BG, color: WHITE, fontFamily: "Inter, Arial, sans-serif", opacity: fade }}>
      <DotGrid />
      <div style={{ position: "absolute", left: 74, right: 74, top: 54, display: "flex", justifyContent: "space-between", alignItems: "center", color: MUTED, fontSize: 18, letterSpacing: 3 }}>
        <span>GAMOTA · RESEARCH MCP</span><span>{n} / 06</span>
      </div>
      <div style={{ position: "absolute", left: 74, top: 142, right: 74, bottom: 100, translate: `0px ${lift}px` }}>{children}</div>
      <div style={{ position: "absolute", left: 74, right: 74, bottom: 52, height: 2, backgroundColor: "#26384b" }}>
        <div style={{ height: "100%", width: `${Math.min(100, (f / (15 * fps)) * 100)}%`, backgroundColor: CYAN }} />
      </div>
      <div style={{ position: "absolute", right: 74, bottom: 69, fontSize: 14, color: MUTED }}>{label}</div>
    </AbsoluteFill>
  );
};

const Kicker: React.FC<{ children: string }> = ({ children }) => <div style={{ color: CYAN, textTransform: "uppercase", letterSpacing: 4, fontSize: 18, fontWeight: 700, marginBottom: 20 }}>{children}</div>;
const Headline: React.FC<{ children: React.ReactNode }> = ({ children }) => <div style={{ fontSize: 58, lineHeight: 1.08, fontWeight: 750, maxWidth: 1000, letterSpacing: -1.8 }}>{children}</div>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <div style={{ fontSize: 25, color: MUTED, lineHeight: 1.45, marginTop: 24, maxWidth: 930 }}>{children}</div>;
const Card: React.FC<{ title: string; body: string; accent?: string }> = ({ title, body, accent = CYAN }) => (
  <div style={{ backgroundColor: PANEL, border: "1px solid #26384b", borderTop: `3px solid ${accent}`, borderRadius: 18, padding: "26px 28px", flex: 1, minHeight: 150 }}>
    <div style={{ color: accent, fontSize: 17, textTransform: "uppercase", letterSpacing: 2, fontWeight: 700 }}>{title}</div>
    <div style={{ color: WHITE, fontSize: 24, lineHeight: 1.35, marginTop: 16 }}>{body}</div>
  </div>
);

export const MyComponent: React.FC<Props> = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <Sequence durationInFrames={450} premountFor={fps}><Frame n="01" label="THE PROBLEM"><Kicker>Evidence before confidence</Kicker><Headline>A citation can be real.<br />The conclusion can still be wrong.</Headline><Sub>When platform, metric or time window changes, a confident research answer can quietly compare unlike things.</Sub><div style={{ display: "flex", gap: 18, marginTop: 42, maxWidth: 900 }}><Card title="Metric" body="Downloads ≠ revenue" /><Card title="Platform" body="Mobile ≠ PC + mobile" /><Card title="Period" body="First month ≠ lifetime" /></div></Frame></Sequence>
      <Sequence from={390} durationInFrames={450} premountFor={fps}><Frame n="02" label="THE SYSTEM"><Kicker>Host-led research · MCP-backed evidence</Kicker><Headline>The agent searches.<br />The system makes findings checkable.</Headline><Sub>Codex or Claude keeps its native web research tools. Gamota MCP supplies the structured evidence layer around the work.</Sub><div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 48 }}><Card title="01 · Contract" body="Question, scope, required evidence"/><div style={{ color: CYAN, fontSize: 30 }}>→</div><Card title="02 · Evidence" body="Sources, quotes, metrics, periods"/><div style={{ color: CYAN, fontSize: 30 }}>→</div><Card title="03 · Decision" body="Validate, trace, or stop"/></div></Frame></Sequence>
      <Sequence from={780} durationInFrames={450} premountFor={fps}><Frame n="03" label="R1 · GROUNDED SUCCESS"><Kicker>Good case · Pokémon TCG Pocket</Kicker><Headline>From a research question<br />to a traceable result.</Headline><Sub>Real web research was stored through MCP. The claims resolve back to evidence and sources; required coverage is complete.</Sub><div style={{ display: "flex", gap: 22, marginTop: 46 }}><Card title="4 claims" body="Validated and linked to evidence"/><Card title="Coverage" body="All required slots covered"/><Card title="Outcome" body="COMPLETE · grounded"/></div></Frame></Sequence>
      <Sequence from={1170} durationInFrames={510} premountFor={fps}><Frame n="04" label="R2 · THE DIFFERENTIATOR"><Kicker>Hard case · Wuthering Waves</Kicker><Headline>Valid claims do not<br />always make a sufficient answer.</Headline><Sub>Seven claims were valid. But the exact first-30-day, mobile-only revenue evidence was missing.</Sub><div style={{ display: "flex", gap: 22, marginTop: 42 }}><Card title="Evidence found" body="Estimates with different scope"/><Card title="Required slot" body="First 30 days · mobile only" accent="#ffbd69"/><Card title="Safe result" body="PARTIAL · WEAK · GAP" accent="#ff7f7f"/></div><div style={{ marginTop: 26, color: CYAN, fontSize: 22, fontWeight: 700 }}>No substituting PC + mobile or later-period figures.</div></Frame></Sequence>
      <Sequence from={1620} durationInFrames={450} premountFor={fps}><Frame n="05" label="TRACEABILITY + VERIFICATION"><Kicker>Inspect every step</Kicker><Headline>Claim → evidence → source<br />→ lineage.</Headline><Sub>Reviewers can follow the path behind a conclusion, inspect the scope and see why the validator accepted it—or why the run stopped short.</Sub><div style={{ display: "flex", gap: 18, marginTop: 46 }}><Card title="97" body="automated tests passed"/><Card title="8 / 8" body="behavior evals passed"/><Card title="15 tools" body="Codex host smoke + reconnect"/></div></Frame></Sequence>
      <Sequence from={2010} durationInFrames={390} premountFor={fps}><Frame n="06" label="STATUS · 2026-10-15"><Kicker>Prototype ready · hosted endpoint pending</Kicker><Headline>Research should earn<br />its confidence.</Headline><Sub>Streamable HTTP passed local bearer-auth checks. Production deployment to the AITC server still requires the operator’s deployment step.</Sub><div style={{ marginTop: 38, display: "inline-flex", border: `1px solid ${CYAN}`, borderRadius: 999, padding: "15px 23px", color: CYAN, fontSize: 20, letterSpacing: 1 }}>VALID CLAIMS ≠ SUFFICIENT ANSWER</div></Frame></Sequence>
    </AbsoluteFill>
  );
};
