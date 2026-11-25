---
description: >-
  The three places a workflow can run, where sensitive data lives in each,
  and what crosses to OpenAdapt.
---

# Deployment boundaries

Every deployment runs the same engine with the same checks and writes the
same reports. Deployments differ in where the runner is and what may cross
to OpenAdapt.

<figure class="oa-diagram-frame">
<svg viewBox="0 0 980 404" role="img" aria-labelledby="oa-db-title oa-db-desc">
  <title id="oa-db-title">OpenAdapt deployment boundaries and data flow</title>
  <desc id="oa-db-desc">Three deployment lanes: Managed browser inside OpenAdapt Cloud for public non-regulated web apps; Customer-controlled runner inside customer infrastructure driving browsers, native apps, or internal systems with an independent read of the system of record; and Remote session driving RDP or Citrix client windows from pixels. An optional OpenAdapt Cloud control plane receives only approved sanitized copies, counts, and digests across the boundary.</desc>
  <defs>
    <marker id="db-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-accent"/>
    </marker>
    <marker id="db-arr-v" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-verified"/>
    </marker>
    <marker id="db-arr-m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M0,1 L9,5 L0,9 z" class="oa-svg-arrow-muted"/>
    </marker>
  </defs>

  <!-- Lane 1: Managed browser -->
  <rect x="14" y="14" width="952" height="84" rx="12" class="oa-svg-panel-link"/>
  <text x="30" y="34" font-size="9.5" class="oa-svg-accent">LANE 1 · MANAGED BROWSER (PUBLIC HTTPS, NO REGULATED DATA)</text>

  <g class="oa-svg-node">
    <rect x="30" y="44" width="248" height="42" rx="8" class="oa-svg-panel"/>
    <text x="44" y="63" font-size="12" class="oa-svg-title">OpenAdapt Cloud</text>
    <text x="44" y="78" font-size="10" class="oa-svg-muted">Control plane &amp; scheduling</text>
  </g>
  <path d="M278,65 L350,65" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#db-arr)"/>
  <g class="oa-svg-node">
    <rect x="356" y="44" width="256" height="42" rx="8" class="oa-svg-panel"/>
    <text x="370" y="63" font-size="12" class="oa-svg-title">Managed browser runner</text>
    <text x="370" y="78" font-size="10" class="oa-svg-muted">Isolated headless container</text>
  </g>
  <path d="M612,65 L684,65" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#db-arr)"/>
  <g class="oa-svg-node">
    <rect x="690" y="44" width="260" height="42" rx="8" class="oa-svg-panel"/>
    <text x="704" y="63" font-size="12" class="oa-svg-title">Public HTTPS web app</text>
    <text x="704" y="78" font-size="10" class="oa-svg-muted">No regulated or patient data</text>
  </g>

  <!-- Lane 2: Customer-controlled runner -->
  <rect x="14" y="112" width="952" height="118" rx="12" class="oa-svg-panel-verified"/>
  <text x="30" y="132" font-size="9.5" class="oa-svg-verified-txt">LANE 2 · CUSTOMER-CONTROLLED RUNNER (REGULATED WORKLOADS STAY INSIDE)</text>

  <g class="oa-svg-node">
    <rect x="30" y="144" width="286" height="58" rx="8" class="oa-svg-panel"/>
    <circle cx="300" cy="158" r="3.5" class="oa-svg-gate-dot oa-svg-dot-verified"/>
    <text x="44" y="165" font-size="12.5" class="oa-svg-title">Runner on your infrastructure</text>
    <text x="44" y="182" font-size="10" class="oa-svg-muted">Workstation, server, VM, or VPC</text>
    <text x="44" y="195" font-size="9.5" class="oa-svg-mono">screens &amp; typed values stay local</text>
  </g>
  <path d="M316,162 L392,162" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#db-arr)"/>
  <g class="oa-svg-node">
    <rect x="398" y="144" width="248" height="58" rx="8" class="oa-svg-panel"/>
    <text x="412" y="165" font-size="12.5" class="oa-svg-title">Target application</text>
    <text x="412" y="182" font-size="10" class="oa-svg-muted">Browser, native desktop app,</text>
    <text x="412" y="195" font-size="10" class="oa-svg-muted">or internal line-of-business app</text>
  </g>
  <path d="M646,162 L714,162" class="oa-svg-line-muted" marker-end="url(#db-arr-m)"/>
  <path d="M316,192 C450,214 590,214 714,192" class="oa-svg-line-verified oa-svg-flow-slow" marker-end="url(#db-arr-v)"/>
  <text x="515" y="223" text-anchor="middle" font-size="9.5" class="oa-svg-verified-txt">independent record read</text>
  <g class="oa-svg-node">
    <rect x="720" y="144" width="230" height="58" rx="8" class="oa-svg-panel-verified"/>
    <text x="734" y="165" font-size="12.5" class="oa-svg-title">System of record</text>
    <text x="734" y="182" font-size="10" class="oa-svg-muted">API or database confirmation</text>
    <text x="734" y="195" font-size="9.5" class="oa-svg-verified-txt">VERIFIED outcome</text>
  </g>

  <!-- Lane 3: Remote session -->
  <rect x="14" y="244" width="952" height="84" rx="12" class="oa-svg-panel"/>
  <text x="30" y="264" font-size="9.5" class="oa-svg-accent">LANE 3 · REMOTE SESSION (NOTHING INSTALLED INSIDE REMOTE HOST)</text>

  <g class="oa-svg-node">
    <rect x="30" y="274" width="248" height="42" rx="8" class="oa-svg-panel"/>
    <text x="44" y="293" font-size="12" class="oa-svg-title">Runner you control</text>
    <text x="44" y="308" font-size="10" class="oa-svg-muted">Local data policy enforced</text>
  </g>
  <path d="M278,295 L350,295" class="oa-svg-line-accent oa-svg-flow" marker-end="url(#db-arr)"/>
  <g class="oa-svg-node">
    <rect x="356" y="274" width="256" height="42" rx="8" class="oa-svg-panel"/>
    <text x="370" y="293" font-size="12" class="oa-svg-title">RDP or Citrix client window</text>
    <text x="370" y="308" font-size="10" class="oa-svg-muted">Pixels, keyboard, and mouse</text>
  </g>
  <path d="M612,295 L684,295" class="oa-svg-line-muted" marker-end="url(#db-arr-m)"/>
  <g class="oa-svg-node">
    <rect x="690" y="274" width="260" height="42" rx="8" class="oa-svg-panel"/>
    <text x="704" y="293" font-size="12" class="oa-svg-title">Remote session</text>
    <text x="704" y="308" font-size="10" class="oa-svg-muted">Needs external API/DB for VERIFIED</text>
  </g>

  <!-- Optional Cloud control plane bar -->
  <rect x="14" y="342" width="952" height="46" rx="10" class="oa-svg-panel-warn"/>
  <text x="30" y="362" font-size="11.5" class="oa-svg-title">Optional OpenAdapt Cloud control plane</text>
  <text x="30" y="378" font-size="10" class="oa-svg-muted">Accounts, versions, run history · Only approved sanitized copies, counts, and SHA-256 digests cross from Lanes 2 &amp; 3. Offline deployments send nothing.</text>
</svg>
<figcaption class="oa-diagram-caption">
  <span><strong>Trust boundaries:</strong> Regulated values, screenshots, and credentials never leave customer-controlled infrastructure.</span>
  <span><a href="../data-handling/">Data handling &rarr;</a></span>
</figcaption>
</figure>

## Managed browser

OpenAdapt runs the control plane and a browser runner. This is for public
HTTPS web apps and data that isn't regulated. Patient data and other
regulated workloads don't belong here and aren't admitted. Desktop, RDP, and
Citrix jobs never go to this runner.

## Customer-controlled runner

The runner is on infrastructure you control: a workstation, a server, a
virtual machine, or your own cloud account. This is the standard choice for
regulated work. Screens, typed values, and record-check results stay inside.
If you connect it to OpenAdapt Cloud, only approved sanitized copies, halt
reports without patient data, and digests cross. A fully offline deployment
sends nothing.

## Remote session

The runner is yours, but the application is in an RDP, Citrix, or other
virtual desktop session. OpenAdapt drives the client window from pixels,
keyboard, and mouse, and installs nothing in the remote session. The rendered
frames are handled under the runner's local data policy. `VERIFIED` still needs a record check that
doesn't go through the session being driven, such as the application's API
or database. Where only the client window's pixels are available, the run
can't end `VERIFIED`, and high-risk workflows may not qualify.

## In every deployment

- Secrets are referenced by name and supplied at run time. They never enter
  artifacts.
- Raw recordings and bundles don't cross a boundary. Only approved sanitized
  copies do.
- The acceptance target is zero runs that report success while the record
  disagrees.
