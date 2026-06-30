<script lang="ts">
  import { figureUrl } from "../lib/api";
  import type { Report } from "../lib/types";

  let { report, jobId }: { report: Report; jobId: string } = $props();

  const unverified = $derived(
    report.results.filter((claim) => claim.verified === false).length,
  );
</script>

<article class="report">
  <h2>Report</h2>

  {#if unverified > 0}
    <p class="warn">
      ⚠ {unverified} result(s) could not be traced to the cited step — treat as unverified.
    </p>
  {/if}

  <section>
    <h3>Question</h3>
    <p>{report.question}</p>
  </section>
  <section>
    <h3>Data</h3>
    <p>{report.data_summary}</p>
  </section>
  <section>
    <h3>Method</h3>
    <p>{report.method}</p>
  </section>
  <section>
    <h3>Assumption checks</h3>
    <p>{report.assumption_checks}</p>
  </section>

  <section>
    <h3>Results</h3>
    {#if report.results.length === 0}
      <p class="muted">No quantitative results.</p>
    {:else}
      <ul class="claims">
        {#each report.results as claim, i (i)}
          <li>
            <strong>{claim.label}:</strong>
            {claim.value}
            <span class="cite">[step {claim.step}]</span>
            {#if claim.verified === false}
              <span class="badge bad">unverified</span>
            {:else if claim.verified}
              <span class="badge ok">verified</span>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  {#if report.figures.length > 0}
    <section>
      <h3>Figures</h3>
      <div class="figures">
        {#each report.figures as figure, i (i)}
          <figure>
            <img
              src={figureUrl(jobId, figure.path)}
              alt={figure.caption}
              loading="lazy"
            />
            <figcaption>
              {figure.caption}{#if figure.step != null}&nbsp;(visualises step {figure.step}){/if}
            </figcaption>
          </figure>
        {/each}
      </div>
    </section>
  {/if}

  <section>
    <h3>Interpretation</h3>
    <p>{report.interpretation}</p>
  </section>
  <section>
    <h3>Caveats</h3>
    <p>{report.caveats}</p>
  </section>
</article>

<style>
  .report {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem;
  }
  h2 {
    margin-top: 0;
  }
  h3 {
    font-size: 0.95rem;
    margin: 1rem 0 0.25rem;
    color: var(--accent);
  }
  section p {
    margin: 0;
  }
  .warn {
    padding: 0.6rem 0.8rem;
    border: 1px solid var(--warn);
    border-radius: 8px;
    background: color-mix(in srgb, var(--warn) 12%, transparent);
  }
  .claims {
    margin: 0;
    padding-left: 1.1rem;
    display: grid;
    gap: 0.3rem;
  }
  .cite {
    color: var(--muted);
    font-size: 0.85em;
  }
  .badge {
    font-size: 0.7rem;
    padding: 0.05rem 0.4rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .badge.ok {
    color: var(--ok);
    border: 1px solid var(--ok);
  }
  .badge.bad {
    color: var(--bad);
    border: 1px solid var(--bad);
  }
  .figures {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  }
  figure {
    margin: 0;
  }
  img {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: #fff;
  }
  figcaption {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.3rem;
  }
  .muted {
    color: var(--muted);
  }
</style>
