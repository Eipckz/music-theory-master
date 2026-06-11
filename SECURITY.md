# Security Policy

## The no-network guarantee

Music Theory Master makes **zero network calls at runtime**. There are no
accounts, no telemetry, no update checks. This is enforced by an automated
test (`tests/test_netsafety.py`) that blocks all socket creation and proves
the app still boots, renders, and grades exercises.

The only code that ever touches the network is `build/fetch_audio_assets.py`,
a build-time tool that downloads the FluidSynth runtime and a SoundFont from
pinned, immutable releases and verifies them against hard-coded SHA-256
hashes before use.

## Other hardening (test-enforced)

- No `eval`, `exec`, or `pickle` anywhere in the codebase.
- All SQL is parameterized.
- Settings are schema-validated JSON; a corrupted file degrades to defaults
  instead of executing anything.
- Release artifacts ship with SHA-256 checksums; verify your download against
  the `.sha256` file on the Releases page.

## Reporting a vulnerability

Please open a private security advisory on GitHub
(Security tab -> "Report a vulnerability") or contact the maintainer
(@Eipckz). Expect an initial response within a week. Please do not open
public issues for unpatched vulnerabilities.
