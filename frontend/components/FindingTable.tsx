"use client";

import { ChevronRight } from "lucide-react";
import type { FindingRow } from "@/lib/types";
import { date, IMPACT_WORDS, percent, rupees } from "@/lib/format";
import { CATEGORY_TONE, Pill, StatusPill } from "./ui";

export function FindingTable({ rows, onOpen, showStatus = false }: { rows: FindingRow[]; onOpen: (id: string) => void; showStatus?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-line text-left text-ink-3">
            <th className="px-3 py-2 font-semibold">Record</th>
            <th className="px-3 py-2 font-semibold">Party</th>
            <th className="px-3 py-2 font-semibold">Finding</th>
            <th className="px-3 py-2 text-right font-semibold">Rupee impact</th>
            <th className="px-3 py-2 text-right font-semibold">How sure</th>
            <th className="px-3 py-2 font-semibold">Deadline</th>
            {showStatus && <th className="px-3 py-2 font-semibold">Status</th>}
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {rows.map((f) => (
            <tr
              key={f.id}
              tabIndex={0}
              role="button"
              aria-label={`Open Finding: ${f.title}`}
              onClick={() => onOpen(f.id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen(f.id))}
              className="cursor-pointer border-b border-line-2 hover:bg-cream-2 focus-visible:bg-cream-2"
            >
              <td className="px-3 py-2.5 font-mono">{f.record_refs[0]?.id}</td>
              <td className="max-w-[200px] truncate px-3 py-2.5">{f.party?.name ?? "Company"}</td>
              <td className="px-3 py-2.5">
                <Pill tone={CATEGORY_TONE[f.category]}>{f.label}</Pill>
              </td>
              <td className="px-3 py-2.5 text-right font-mono">
                {f.impact_type === "none" ? (
                  <span className="text-ink-3">none</span>
                ) : (
                  <>
                    {rupees(f.impact_paise)} <span className="font-sans text-[12px] text-ink-3">{IMPACT_WORDS[f.impact_type]}</span>
                  </>
                )}
              </td>
              <td className="px-3 py-2.5 text-right font-mono">{percent(f.confidence)}</td>
              <td className="px-3 py-2.5 text-ink-2">{f.deadline ? date(f.deadline) : ""}</td>
              {showStatus && (
                <td className="px-3 py-2.5">
                  <StatusPill status={f.status} />
                </td>
              )}
              <td className="px-3 py-2.5 text-right font-semibold text-orange-deep">
                <span className="inline-flex items-center gap-0.5">
                  See why and fix <ChevronRight className="size-4" aria-hidden />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
