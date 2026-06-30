// TypeScript mirrors of the backend payloads (statskills_api: stream.py + reporting schema).
// Kept in sync by hand — the surface is small and stable.

export type Delivery = "off" | "injected" | "agentic";

export type StepKind =
  "thought" | "code" | "observation" | "final" | "status" | "error";

/** One streamed event from a run (StepEvent.to_dict()); fields are populated per kind. */
export interface StepEvent {
  kind: StepKind;
  index?: number;
  text?: string;
  code?: string;
  observation?: string;
  ok?: boolean;
}

/** A traceable quantitative finding; `verified` is null before the backend checks it. */
export interface Claim {
  label: string;
  value: string;
  step: number;
  verified: boolean | null;
}

/** A report-time diagnostic figure; `path` is relative to the report. */
export interface Figure {
  path: string;
  caption: string;
  step: number | null;
}

/** The composed §10 report. */
export interface Report {
  task_id: string;
  question: string;
  data_summary: string;
  method: string;
  assumption_checks: string;
  results: Claim[];
  interpretation: string;
  caveats: string;
  figures: Figure[];
}

export type RunStatus = "running" | "done" | "error";

/** GET /runs/{id} — status plus the report (when done) or an error message. */
export interface RunState {
  job_id: string;
  status: RunStatus;
  report?: Report;
  error?: string;
}
