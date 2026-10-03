"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { DatasetInfo, StageEvent, Summary } from "./types";

export const DEFAULT_PERIOD = "2025-09";
type RunState = "idle" | "loading" | "running" | "done" | "failed";

type Store = {
  ready: boolean;
  loadError: string | null;
  dataset: DatasetInfo | null;
  period: string;
  runId: string | null;
  summary: Summary | null;
  stages: StageEvent[];
  runState: RunState;
  runError: string | null;
  launch: (period?: string) => Promise<boolean>;
  choosePeriod: (period: string) => Promise<void>;
  setSummary: (summary: Summary) => void;
  refresh: () => Promise<void>;
  retry: () => void;
};

const RunContext = createContext<Store | null>(null);

export function RunProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [dataset, setDataset] = useState<DatasetInfo | null>(null);
  const [period, setPeriod] = useState(DEFAULT_PERIOD);
  const [runId, setRunId] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [runState, setRunState] = useState<RunState>("idle");
  const [runError, setRunError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const source = useRef<EventSource | null>(null);

  const adopt = useCallback(async (id: string) => {
    const next = await api.summary(id);
    setRunId(id);
    setSummary(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    api
      .latest(DEFAULT_PERIOD)
      .then(async ({ run, dataset: loaded }) => {
        if (cancelled) return;
        setDataset(loaded);
        if (run) await adopt(run.run_id);
      })
      .catch((error: ApiError) => !cancelled && setLoadError(error.message))
      .finally(() => !cancelled && setReady(true));
    return () => {
      cancelled = true;
      source.current?.close();
    };
  }, [adopt, attempt]);

  const launch = useCallback(
    async (target?: string) => {
      const wanted = target ?? period;
      setStages([]);
      setRunError(null);
      setRunState("loading");
      try {
        const loaded = dataset ?? (await api.loadDemo());
        setDataset(loaded);
        const { run_id } = await api.startRun(loaded.dataset_id, wanted);
        setRunState("running");
        const finished = await new Promise<boolean>((resolve) => {
          const events = new EventSource(api.eventsUrl(run_id));
          source.current = events;
          events.addEventListener("stage", (e) => setStages((all) => [...all, JSON.parse((e as MessageEvent).data)]));
          events.addEventListener("done", () => {
            events.close();
            resolve(true);
          });
          events.addEventListener("failed", (e) => {
            events.close();
            setRunError(JSON.parse((e as MessageEvent).data).message);
            resolve(false);
          });
          // If the stream drops, ask the Run itself until it reaches an end state.
          events.onerror = async () => {
            events.close();
            for (;;) {
              const run = await api.run(run_id).catch(() => null);
              if (run?.status === "done") return resolve(true);
              if (!run || run.status === "failed") {
                setRunError(run?.error ?? "Lost contact with the server during the Run.");
                return resolve(false);
              }
              await new Promise((r) => setTimeout(r, 500));
            }
          };
        });
        if (!finished) {
          setRunState("failed");
          return false;
        }
        setPeriod(wanted);
        await adopt(run_id);
        setRunState("done");
        return true;
      } catch (error) {
        setRunError((error as Error).message);
        setRunState("failed");
        return false;
      }
    },
    [adopt, dataset, period],
  );

  const choosePeriod = useCallback(
    async (next: string) => {
      const { run } = await api.latest(next);
      if (run) {
        setPeriod(next);
        await adopt(run.run_id);
      } else {
        await launch(next);
      }
    },
    [adopt, launch],
  );

  const refresh = useCallback(async () => {
    if (runId) setSummary(await api.summary(runId));
  }, [runId]);

  const value = useMemo<Store>(
    () => ({ ready, loadError, dataset, period, runId, summary, stages, runState, runError, launch, choosePeriod, setSummary, refresh, retry: () => setAttempt((n) => n + 1) }),
    [ready, loadError, dataset, period, runId, summary, stages, runState, runError, launch, choosePeriod, refresh],
  );
  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRun(): Store {
  const store = useContext(RunContext);
  if (!store) throw new Error("useRun must be used inside RunProvider");
  return store;
}
