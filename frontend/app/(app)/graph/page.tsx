"use client";

import { useEffect, useRef, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useRun } from "@/lib/run-store";
import { periodName, rupeesShort } from "@/lib/format";
import type { Graph } from "@/lib/types";
import { ErrorState, PageTitle, Skeleton } from "@/components/ui";

const COLOURS = { company: "#F28C3A", ring: "#D64545", cancelled: "#C98A12", clean: "#5B9079" };

export default function GraphPage() {
  const { runId, summary } = useRun();
  const [graph, setGraph] = useState<Graph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const canvas = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!runId) return;
    setError(null);
    setGraph(null);
    api
      .graph(runId)
      .then((g) => {
        setGraph(g);
        setSelected(g.rings[0]?.id ?? null);
      })
      .catch((e: Error) => setError(e.message));
  }, [runId]);

  useEffect(() => {
    if (!graph || !canvas.current) return;
    let cy: import("cytoscape").Core | undefined;
    let cancelled = false;
    import("cytoscape").then(({ default: cytoscape }) => {
      if (cancelled || !canvas.current) return;
      const names = new Map(graph.nodes.map((n) => [n.id, n]));
      // The Company sits left of centre, ordinary Parties fan out behind it and linked Parties stand apart on the right.
      const risky = graph.nodes.filter((n) => n.kind !== "company" && n.risk !== "clean");
      const plain = graph.nodes.filter((n) => n.risk === "clean" && n.kind !== "company").slice(0, 18);
      const shown = new Set(["company", ...risky.map((n) => n.id), ...plain.map((n) => n.id)]);
      const position = new Map<string, { x: number; y: number }>([["company", { x: 0, y: 0 }]]);
      plain.forEach((n, i) => {
        const angle = (Math.PI * (100 + (160 * i) / Math.max(1, plain.length - 1))) / 180;
        const radius = i % 2 ? 300 : 220;
        position.set(n.id, { x: Math.cos(angle) * radius, y: -Math.sin(angle) * radius });
      });
      risky.forEach((n, i) => {
        const angle = (Math.PI * (55 - (110 * i) / Math.max(1, risky.length - 1))) / 180;
        position.set(n.id, { x: Math.cos(angle) * 330, y: -Math.sin(angle) * 250 });
      });
      cy = cytoscape({
        container: canvas.current,
        elements: [
          ...graph.nodes.filter((n) => shown.has(n.id)).map((n) => ({
            position: position.get(n.id),
            data: {
              id: n.id,
              label: n.kind === "company" ? "You" : n.risk === "clean" ? "" : `${n.label}\n${n.risk === "cancelled" ? "GSTIN cancelled" : n.kind === "supplier" ? "your supplier" : "your customer"}`,
              name: n.label,
              colour: n.kind === "company" ? COLOURS.company : COLOURS[n.risk],
              size: n.kind === "company" ? 88 : n.risk === "clean" ? 24 : 58,
              level: n.kind === "company" ? 3 : n.risk === "clean" ? 1 : 2,
              risk: n.risk,
            },
          })),
          ...graph.edges.filter((e) => shown.has(e.source) && shown.has(e.target)).map((e, i) => ({
            data: {
              id: `e${i}`,
              source: e.source,
              target: e.target,
              kind: e.kind,
              label: e.kind === "trade" ? "" : e.label.replace(/ [A-Z0-9]{10}$/, ""),
              risky: e.kind !== "trade" || names.get(e.target)?.risk !== "clean",
            },
          })),
        ],
        layout: { name: "preset", padding: 70 },
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(colour)",
              width: "data(size)",
              height: "data(size)",
              label: "data(label)",
              color: "#FFF7EC",
              "font-family": "Inter, system-ui, sans-serif",
              "font-size": 15,
              "font-weight": 600,
              "text-wrap": "wrap",
              "text-valign": "bottom",
              "text-margin-y": 8,
              "line-height": 1.35,
              "border-width": 3,
              "border-color": "rgba(255,255,255,0.35)",
            },
          },
          { selector: "node[level = 3]", style: { "text-valign": "center", "text-margin-y": 0, color: "#24110C", "font-size": 20, "font-weight": 700 } },
          { selector: "node[level = 1]", style: { "border-width": 0, opacity: 0.9 } },
          { selector: "edge", style: { width: 1.2, "line-color": "rgba(255,239,216,0.22)", "curve-style": "bezier" } },
          { selector: "edge[?risky][kind = 'trade']", style: { width: 3, "line-color": COLOURS.company } },
          {
            selector: "edge[kind != 'trade']",
            style: {
              width: 3,
              "line-color": "#F26D6D",
              "line-style": "dashed",
              label: "data(label)",
              color: "#FF9A9A",
              "font-size": 13,
              "font-weight": 600,
              "text-background-color": "#211815",
              "text-background-opacity": 1,
              "text-background-padding": "4px",
              "curve-style": "unbundled-bezier",
              "control-point-distances": [90],
              "control-point-weights": [0.5],
            },
          },
        ],
        userZoomingEnabled: false,
        boxSelectionEnabled: false,
      });
      cy.on("tap", "node", (event) => {
        const id = event.target.id();
        const ring = graph.rings.find((r) => r.members.includes(id));
        if (ring) setSelected(ring.id);
      });
    });
    return () => {
      cancelled = true;
      cy?.destroy();
    };
  }, [graph]);

  if (error) return <ErrorState message={error} />;

  const ring = graph?.rings.find((r) => r.id === selected) ?? null;
  const names = new Map(graph?.nodes.map((n) => [n.id, n.label]) ?? []);
  const clean = graph?.nodes.filter((n) => n.risk === "clean").length ?? 0;

  return (
    <div>
      <PageTitle
        title="Ring view"
        lead="Who you trade with, and which of them are linked. A Supplier and a Customer with the same PAN have one owner, so money and credit can move in a circle."
      />
      <div className="relative overflow-hidden rounded-xl bg-[#211815]" style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }}>
        {!graph ? <Skeleton className="h-[620px] opacity-20" /> : <div ref={canvas} className="h-[620px] w-[calc(100%-390px)]" role="img" aria-label={`Network of the Company and its Parties for ${summary ? periodName(summary.period) : "the period"}. ${graph.rings.length} linked groups.`} />}

        {graph && (
          <aside className="absolute right-4 top-4 flex max-h-[588px] w-[360px] flex-col gap-3 overflow-y-auto">
            {graph.rings.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-[#2B211D] p-4 text-cream">No linked Parties in this period.</div>
            ) : (
              graph.rings.map((r) => {
                const active = r.id === ring?.id;
                const isRing = r.id.startsWith("ring");
                return (
                  <button
                    key={r.id}
                    onClick={() => setSelected(r.id)}
                    aria-pressed={active}
                    className={`rounded-xl border p-4 text-left text-cream ${active ? "border-[#F26D6D]/70 bg-[#2B211D]" : "border-white/10 bg-[#2B211D]/80 opacity-80 hover:opacity-100"}`}
                  >
                    <p className={`mb-1.5 flex items-center gap-2 font-display text-[18px] font-bold ${isRing ? "text-[#FF8A8A]" : "text-[#F2B85A]"}`}>
                      <ShieldAlert className="size-5" aria-hidden />
                      {isRing ? "Supplier and Customer, one owner" : "Cancelled GSTIN"}
                    </p>
                    <p className="text-[12px] text-cream/60">{r.members.map((m) => names.get(m) ?? m).join(" and ")}</p>
                    {active && <p className="mt-2 text-[14px] leading-relaxed">{r.reason}</p>}
                    <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1 text-[13px] text-cream/70">
                      <dt>Credit at risk this month</dt>
                      <dd className="text-right font-mono font-semibold text-orange">{rupeesShort(r.itc_at_risk_paise)}</dd>
                      <dt>{isRing ? "Invoices with them" : "Invoices after cancellation"}</dt>
                      <dd className="text-right font-mono font-semibold text-white">{r.invoice_count}</dd>
                    </dl>
                  </button>
                );
              })
            )}
          </aside>
        )}

        <ul className="absolute bottom-3 left-4 flex flex-wrap gap-4 text-[13px] text-cream/80">
          {[
            ["Your company", COLOURS.company],
            ["Linked by one PAN", COLOURS.ring],
            ["Cancelled GSTIN", COLOURS.cancelled],
            [`Other Parties (${Math.min(clean, 18)} largest shown)`, COLOURS.clean],
          ].map(([label, colour]) => (
            <li key={label} className="flex items-center gap-2">
              <span className="size-2.5 rounded-full" style={{ background: colour }} aria-hidden />
              {label}
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-2 text-[13px] text-ink-3">LedgerLens reports the link and what it puts at stake. It does not call anyone a fraud; a person decides what the link means.</p>
    </div>
  );
}
