# CL-000003 — Brain Cinematic Film Channel Request

## Customer request
CL-000003 requests that Brain create and operate a dedicated video channel/page with a YouTube-like viewing experience, containing **only original films produced by Brain**.

The channel is not a general upload area. Publication is conditional on the Cinematic Master Release Gate.

## Core rule
A film must **not** be released merely because it renders successfully, passes technical QC, or produces an MP4.

If the film fails the professional cinematic gate, Brain must:
1. block publication;
2. record failure evidence and failed criteria;
3. diagnose root causes;
4. repair/rework or reject the production;
5. produce a new/revised film;
6. rerun the full validation pipeline;
7. repeat until a film passes the release gate or the bounded production policy requires escalation/stop.

## Professional cinematic gate
The gate evaluates, at minimum:
- story/narrative coherence and completeness;
- screenplay/dialogue quality;
- directing and scene continuity;
- acting/character performance where applicable;
- cinematography, framing, composition and visual continuity;
- lighting, color, exposure and visual consistency;
- production design/world consistency;
- editing, pacing, rhythm and transitions;
- sound design, dialogue intelligibility, ambience and mix;
- music suitability and synchronization;
- visual effects/compositing quality where used;
- titles, credits and metadata quality;
- technical delivery: resolution, frame rate, codec/container, audio, bitrate and playback integrity;
- originality and provenance of generated assets;
- rights/licensing clearance for every non-original or externally sourced asset;
- applicable copyright, privacy, publicity, safety and other laws/rules;
- platform/community requirements applicable to the eventual publishing destination.

Passing technical checks alone is never sufficient.

## Release decision
Required release states: `CINEMATIC_PASS`, `RIGHTS_PASS`, `LEGAL_POLICY_PASS`, `TECHNICAL_PASS`, `MASTER_RELEASE_PASS`.

Any required gate failure => `DO_NOT_PUBLISH`.

## Channel integrity
The channel must maintain an auditable manifest linking each published film to film ID/version, production run, script/story version, asset provenance, QC evidence, cinematic review evidence, rights/legal-policy checks, release decision, and publication record.

No payment, contract, purchase, withdrawal, or financial transaction is created automatically by this request.

## Pipeline
`IDEA -> STORY -> SCRIPT -> PREPRODUCTION -> ASSETS -> VOICE/SOUND -> EDIT -> RENDER -> TECHNICAL_QC -> CINEMATIC_QC -> RIGHTS/LEGAL_POLICY_QC -> MASTER_RELEASE_GATE -> PUBLISH`

Failure path:
`FAIL -> EVIDENCE -> DIAGNOSE -> REWORK/REPLACE -> RENDER -> FULL_RECHECK`

## Acceptance principle
The objective is not to maximize the number of uploaded videos. The objective is to publish only films that meet the defined professional release standard.