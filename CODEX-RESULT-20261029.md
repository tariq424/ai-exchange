# Codex test-branch result — October 29, 2026

Tariq resumed execution, cancelled Higgsfield, allowed controlled Google fallbacks, and later directed testing without HF. He approved only the HF credential loader being applied to the live copy; visual changes stay test-only.

Private code branch: `tariq424/video-studio-test`, `codex/test-fit-vault-20261029`, commit `3b18209`.

- DeepSeek request/answer completed on this exchange test branch using one round of the existing mailman's API logic. The main mailman and mailbox were not changed.
- 42022-only local narration-fit gate for fresh and resumed generated images, rejection evidence, cumulative audit counts and Google-last provider ordering.
- HF token Vault migration/verification/redaction support, with Linux environment fallback. Gemini configuration and Google Photos code retained. No qc.py edits.
- 144 tests pass, 4 browser skips, one known Windows/WSL shell invocation test excluded; explicit Git Bash syntax check passes.
- HF-free offline smoke: one rejected candidate, one accepted candidate, real two-second CPU FFmpeg encode and strict decode pass. Providers/vision mocked; real local-model quality remains to test in an idle GPU window.
- Isolated 42022 server running idle from the test checkout, own jobs/lock paths. Test runtime excludes HF image generation/talking head and paid Flow.
- Approved live credential loader updated on disk, unrelated edits preserved. Existing HF credential stored and verified in Windows Vault without displaying it. No restart or live settings migration while 42021 is rendering. The running process must safely load the new credential code before settings migration; rotation deferred per Tariq.
- Supplied reference document links to Nuli Studio, AI Genesis and Dan Martell, not the named Christian/Matt references. Matching Christian creator notes were reviewed separately; no exact FFmpeg optimization command or speedup verified.

See CODEX_TEST_RESULTS.md and RENDER_REFERENCE_REVIEW.md on the code branch for details. No visual deployment, publishing, deletion or paid generation performed. Other pre-existing merge work is not claimed complete by this result.
