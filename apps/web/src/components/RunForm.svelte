<script lang="ts">
  import type { Delivery } from "../lib/types";

  let {
    onsubmit,
    disabled = false,
  }: {
    onsubmit: (input: { prompt: string; delivery: Delivery; file: File }) => void;
    disabled?: boolean;
  } = $props();

  let prompt = $state("Is the effect of the predictor on the outcome significant?");
  let delivery = $state<Delivery>("agentic");
  let file = $state<File | null>(null);

  const deliveries: { value: Delivery; label: string; hint: string }[] = [
    { value: "off", label: "Off", hint: "no skills — the plain agent" },
    { value: "injected", label: "Injected", hint: "skill bodies in the prompt" },
    { value: "agentic", label: "Agentic", hint: "agent reads skills on demand" },
  ];

  function pickFile(event: Event) {
    file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!file || disabled) return;
    onsubmit({ prompt, delivery, file });
  }
</script>

<form onsubmit={submit}>
  <label class="field">
    <span>Question</span>
    <textarea bind:value={prompt} rows="2" {disabled}></textarea>
  </label>

  <fieldset class="field" {disabled}>
    <legend>Skill delivery</legend>
    <div class="segments">
      {#each deliveries as option (option.value)}
        <label class="segment" class:selected={delivery === option.value}>
          <input
            type="radio"
            name="delivery"
            value={option.value}
            bind:group={delivery}
            {disabled}
          />
          <span class="seg-label">{option.label}</span>
          <span class="seg-hint">{option.hint}</span>
        </label>
      {/each}
    </div>
  </fieldset>

  <label class="field">
    <span>Dataset (CSV)</span>
    <input type="file" accept=".csv,text/csv" onchange={pickFile} {disabled} />
  </label>

  <button type="submit" disabled={disabled || !file}>
    {disabled ? "Running…" : "Analyze"}
  </button>
</form>

<style>
  form {
    display: grid;
    gap: 1rem;
    padding: 1.25rem;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
  }
  .field {
    display: grid;
    gap: 0.4rem;
  }
  .field > span,
  legend {
    font-weight: 600;
    font-size: 0.9rem;
  }
  textarea {
    width: 100%;
    resize: vertical;
    padding: 0.5rem;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    font: inherit;
  }
  fieldset {
    border: none;
    padding: 0;
    margin: 0;
  }
  .segments {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
  }
  .segment {
    display: grid;
    gap: 0.15rem;
    padding: 0.6rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
  }
  .segment.selected {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
  }
  .segment input {
    display: none;
  }
  .seg-label {
    font-weight: 600;
  }
  .seg-hint {
    font-size: 0.78rem;
    color: var(--muted);
  }
  button {
    justify-self: start;
    padding: 0.55rem 1.4rem;
    font: inherit;
    font-weight: 600;
    color: #0b0d12;
    background: var(--accent);
    border: none;
    border-radius: 8px;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.55;
    cursor: default;
  }
</style>
