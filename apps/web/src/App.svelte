<script lang="ts">
  import RunForm from "./components/RunForm.svelte";
  import StepStream from "./components/StepStream.svelte";
  import ReportView from "./components/ReportView.svelte";
  import { fetchRun, streamEvents, submitRun } from "./lib/api";
  import type { Delivery, Report, StepEvent } from "./lib/types";

  type Phase = "idle" | "running" | "done" | "error";

  let phase = $state<Phase>("idle");
  let steps = $state<StepEvent[]>([]);
  let report = $state<Report | null>(null);
  let error = $state<string | null>(null);
  let jobId = $state<string | null>(null);
  let teardown: (() => void) | null = null;

  const running = $derived(phase === "running");

  async function start(input: { prompt: string; delivery: Delivery; file: File }) {
    reset();
    phase = "running";
    try {
      const result = await submitRun(input);
      jobId = result.job_id;
      teardown = streamEvents(result.job_id, {
        onStep: (event) => steps.push(event),
        onDone: () => loadReport(result.job_id),
        onError: (message) => fail(message),
      });
    } catch (e) {
      fail(messageOf(e));
    }
  }

  async function loadReport(id: string) {
    try {
      const state = await fetchRun(id);
      if (state.status === "error") {
        fail(state.error ?? "the run failed");
        return;
      }
      report = state.report ?? null;
      phase = "done";
    } catch (e) {
      fail(messageOf(e));
    }
  }

  function fail(message: string) {
    error = message;
    phase = "error";
    teardown?.();
    teardown = null;
  }

  function reset() {
    teardown?.();
    teardown = null;
    steps = [];
    report = null;
    error = null;
    jobId = null;
  }

  function messageOf(e: unknown): string {
    return e instanceof Error ? e.message : String(e);
  }
</script>

<main>
  <header>
    <h1>statskills</h1>
    <p class="tagline">
      Does <em>how</em> a statistics skill is delivered change the answer? Upload a dataset,
      pick a delivery mode, watch the agent work, then read the traceable report.
    </p>
  </header>

  <RunForm onsubmit={start} disabled={running} />

  {#if error}
    <p class="error" role="alert">{error}</p>
  {/if}

  {#if phase !== "idle"}
    <div class="results">
      <StepStream {steps} {running} />
      {#if report && jobId}
        <ReportView {report} {jobId} />
      {/if}
    </div>
  {/if}
</main>

<style>
  main {
    max-width: 60rem;
    margin: 2rem auto;
    padding: 0 1rem 4rem;
    display: grid;
    gap: 1.5rem;
  }
  h1 {
    margin-bottom: 0.25rem;
  }
  .tagline {
    color: var(--muted);
    max-width: 44rem;
    margin: 0;
  }
  .results {
    display: grid;
    gap: 1.5rem;
  }
  .error {
    padding: 0.7rem 0.9rem;
    border: 1px solid var(--bad);
    border-radius: 8px;
    background: color-mix(in srgb, var(--bad) 12%, transparent);
    margin: 0;
  }
</style>
