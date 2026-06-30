// Typed client for the statskills backend. All URLs are relative: in dev the Vite proxy
// forwards them to the API; in production the API serves these assets same-origin — so the
// browser always sees one origin and never hits CORS.

import type { Delivery, RunState, StepEvent } from "./types";

export interface SubmitResult {
  job_id: string;
}

/** POST /runs — submit a prompt + dataset + delivery toggle; returns the job id. */
export async function submitRun(input: {
  prompt: string;
  delivery: Delivery;
  file: File;
}): Promise<SubmitResult> {
  const form = new FormData();
  form.set("prompt", input.prompt);
  form.set("delivery", input.delivery);
  form.set("file", input.file);
  const resp = await fetch("/runs", { method: "POST", body: form });
  if (!resp.ok) throw new Error(await errorMessage(resp));
  return (await resp.json()) as SubmitResult;
}

/** GET /runs/{id} — the run's status and, once done, its report (or error). */
export async function fetchRun(jobId: string): Promise<RunState> {
  const resp = await fetch(`/runs/${encodeURIComponent(jobId)}`);
  if (!resp.ok) throw new Error(await errorMessage(resp));
  return (await resp.json()) as RunState;
}

export interface StreamHandlers {
  onStep: (event: StepEvent) => void;
  onDone: (status: string) => void;
  onError?: (message: string) => void;
}

/** Open the run's SSE stream. Returns a teardown function that closes the connection. */
export function streamEvents(jobId: string, handlers: StreamHandlers): () => void {
  const source = new EventSource(`/runs/${encodeURIComponent(jobId)}/events`);

  source.addEventListener("step", (event) => {
    handlers.onStep(JSON.parse((event as MessageEvent).data) as StepEvent);
  });
  source.addEventListener("done", (event) => {
    const { status } = JSON.parse((event as MessageEvent).data) as { status: string };
    source.close();
    handlers.onDone(status);
  });
  source.addEventListener("error", () => {
    // The clean end-of-stream path closes the source in the `done` handler above; this
    // fires only on an unexpected drop (network/server). Avoid a duplicate report fetch.
    if (source.readyState === EventSource.CLOSED) return;
    source.close();
    handlers.onError?.("lost connection to the run stream");
  });

  return () => source.close();
}

/** Build the figure-image URL from a report-relative figure path. */
export function figureUrl(jobId: string, path: string): string {
  const name = path.split("/").pop() ?? path;
  return `/runs/${encodeURIComponent(jobId)}/figures/${encodeURIComponent(name)}`;
}

async function errorMessage(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { detail?: unknown };
    if (typeof body?.detail === "string") return `${resp.status}: ${body.detail}`;
  } catch {
    // non-JSON error body — fall through to the generic message
  }
  return `request failed (${resp.status})`;
}
