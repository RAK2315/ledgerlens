"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";
import type { FeedItem, StageEvent } from "@/lib/types";
import { RunFeed } from "../RunFeed";

type Beat = { stage?: StageEvent; item?: FeedItem };

/** Replays a recorded Run in the page: the same feed the app shows, with the real lines of the demo month. */
export function RunDemo({ stages, items }: { stages: StageEvent[]; items: FeedItem[] }) {
  // The recording in the order it happened: a stage starts, its lines go by, it reports what it found.
  const beats = useMemo<Beat[]>(() => {
    const order: Beat[] = [];
    for (const started of stages.filter((s) => s.status === "started")) {
      order.push({ stage: started });
      order.push(...items.filter((i) => i.stage === started.stage).map((item) => ({ item })));
      const done = stages.find((s) => s.stage === started.stage && s.status === "done");
      if (done) order.push({ stage: done });
    }
    return order;
  }, [stages, items]);

  const [shown, setShown] = useState(0);
  const [playing, setPlaying] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  // Start the first time the feed scrolls into view.
  useEffect(() => {
    const node = box.current;
    if (!node) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const watcher = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        watcher.disconnect();
        if (still) setShown(beats.length);
        else setPlaying(true);
      },
      { threshold: 0.25 },
    );
    watcher.observe(node);
    return () => watcher.disconnect();
  }, [beats.length]);

  useEffect(() => {
    if (!playing) return;
    if (shown >= beats.length) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setShown((n) => n + 1), beats[shown].stage ? 320 : 150);
    return () => clearTimeout(timer);
  }, [playing, shown, beats]);

  const seen = beats.slice(0, shown);
  const finished = shown >= beats.length;
  return (
    <div ref={box} className="rounded-[16px] bg-paper px-8 py-6 shadow-float">
      <div className="mb-2 flex items-center justify-between gap-4">
        <p className="font-display text-[22px] font-bold">Reconciling September 2025</p>
        <button
          className="btn"
          onClick={() => {
            setShown(0);
            setPlaying(true);
          }}
          disabled={playing}
        >
          <RotateCcw className="size-4" aria-hidden /> {finished ? "Play again" : "Playing"}
        </button>
      </div>
      <RunFeed stages={seen.flatMap((b) => (b.stage ? [b.stage] : []))} items={seen.flatMap((b) => (b.item ? [b.item] : []))} waiting={!finished} inPage />
    </div>
  );
}
