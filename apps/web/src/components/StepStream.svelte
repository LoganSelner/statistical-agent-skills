<script lang="ts">
  import type { StepEvent, StepKind } from "../lib/types";

  let { steps, running }: { steps: StepEvent[]; running: boolean } = $props();

  const labels: Record<StepKind, string> = {
    thought: "Thought",
    code: "Code",
    observation: "Observation",
    final: "Final answer",
    status: "Status",
    error: "Error",
  };
</script>

<section class="stream">
  <h2>Agent steps</h2>
  {#if steps.length === 0}
    <p class="muted">{running ? "Waiting for the agent…" : "No steps yet."}</p>
  {/if}
  <ol>
    {#each steps as step, i (i)}
      <li class="step step--{step.kind}">
        <span class="kind">
          {labels[step.kind]}{#if step.index != null}&nbsp;· step {step.index}{/if}
        </span>
        {#if step.text}<p class="text">{step.text}</p>{/if}
        {#if step.code}<pre class="code">{step.code}</pre>{/if}
        {#if step.observation}
          <pre class="obs" class:bad={step.ok === false}>{step.observation}</pre>
        {/if}
      </li>
    {/each}
  </ol>
  {#if running && steps.length > 0}
    <p class="muted pulse">running…</p>
  {/if}
</section>

<style>
  .stream {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem;
  }
  h2 {
    margin-top: 0;
    font-size: 1.1rem;
  }
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.6rem;
  }
  .step {
    border-left: 3px solid var(--border);
    padding: 0.2rem 0 0.2rem 0.7rem;
  }
  .step--code {
    border-color: var(--accent);
  }
  .step--final {
    border-color: var(--ok);
  }
  .step--error {
    border-color: var(--bad);
  }
  .step--status {
    border-color: var(--warn);
  }
  .kind {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }
  .text {
    margin: 0.2rem 0;
    white-space: pre-wrap;
  }
  pre {
    margin: 0.3rem 0 0;
    padding: 0.55rem 0.7rem;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .obs.bad {
    border-color: var(--bad);
  }
  .muted {
    color: var(--muted);
  }
  .pulse {
    animation: pulse 1.4s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.4;
    }
  }
</style>
