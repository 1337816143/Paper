# Paper Lab maintenance contract

## Sources and privacy
Paper is the upstream for public academic reading content. Preserve all verified learning content; do not overwrite with summaries. Never publish private chats, recordings, contact details, offer letters, signatures, application documents, credentials or unauthorized PDFs. User-uploaded copyrighted sources may support original explanatory notes, not wholesale redistribution.

Every claim must distinguish article evidence, teaching explanation, synthetic exercise, inference and research-transfer proposal. Preserve original terminology; document errors/contradictions rather than silently reconciling them. Do not label abstract-only reading as full-text close reading. Cite primary sources and exact Methods/figure/section locations when available. Article license does not imply software license.

## After each relevant tutoring conversation
1. Read current content and this contract. Update the relevant paper/method lesson, quiz and cross-links with the new explanation; do not dump raw chat.
2. Store private notes only outside public repositories or keep them on the user's device.
3. Add a dated learning change entry in content/session-log.json (schema: array of ordinary guide documents) when substantive content changes.
4. Run python scripts/build.py and python examples/pareto_lab.py --test, then browser checks. Commit only intended source files. Never force push or delete unrelated work.
5. Wait for the Paper build/deploy workflow. Report exact status; a commit alone is not a deployed website.
6. My-Evolution is the sole editable upstream of Evolution. Synchronize through its pinned Paper source and standard tests/publish workflow. Never edit Evolution directly.

ChatGPT has no general after-conversation webhook exposed here. The agent must perform a real commit; GitHub Actions deploys submitted content, not unsubmitted conversations. Do not claim autonomous access to future chat. A scheduled checker may repair or report missed repository synchronization, but must not invent lessons or infer user progress.

## Architecture
content/*.json -> scripts/build.py -> dist/site. All browser assets are local. Static pages support full-site indexing. Service-worker caches are scoped per path and content version. Offline single HTML embeds lessons/scripts; website ZIP includes examples. No embedded or persisted authorization secrets, analytics or CDN. Explicitly authorized private-vault API access is allowed under the v5 rules below. Reading progress and notes are local, exportable, and must survive application updates.

## Validation
Check internal links, metadata evidence states, mathematical examples, accessibility, mobile overflow, exact back-position restoration, offline refresh and notes export/import. On failure fix the source rather than weakening tests.

## Study layer v3
Preserve English source strings, block IDs and existing local annotations. Framework narratives and glossary definitions must cite actual lessons/sources. Translation is a separate on-device layer, labelled as unreviewed machine output; do not publish translations of NoDerivatives sources. All browser inference assets are local, pinned and license/hash checked. No note or private source goes to an inference API. Math changes are technical presentation only; retain source crops and raw blocks. Run scripts/test_study.py in addition to existing browser/reader tests. Update math overlays on original-source refresh; never silently reinterpret ambiguous symbols.

## Private synchronization v5
The user requested local plus private GitHub persistence. Runtime authorization may exist only in page memory after explicit user entry; never in source, storage, logs, URLs or backup. Verify that the destination repository is private before every synchronization; write only the dedicated paper-user-data branch under private/paper-sync/v5/. Preserve concurrent versions and deletion tombstones. An offline/local save is not a cloud confirmation. Existing browser data is not migrated until the user connects and a checkpoint is acknowledged. Do not claim an OAuth service has been deployed. Public website builds must not contain any vault data. Test actual two-device private GitHub writes using synthetic records and an ephemeral CI token; never include real user notes or credentials in test artifacts.
