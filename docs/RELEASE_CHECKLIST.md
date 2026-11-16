# Release checklist

- [ ] README, CHANGELOG and notices are in English and accurately describe this specific version.
- [ ] Upstream source and MIT license are preserved, with third-party media rights documented separately.
- [ ] The README labels scripted game-state GIFs **as scripted**, not as live game recordings.
- [ ] When available, replace them with verified live Pygame recordings using `tools/record_live_gameplay.py`.
- [ ] Check Windows first-frame Space Hard Drop, Chinese IME handling, and instant top-out in two-player matches.
- [ ] Run `python -m pytest -q`, confirm results and confirm optional media-dependent skips.
- [ ] Verify game audio, visual skins and keyboard controls on a compatible computer.
- [ ] Remove credentials, token files, build artifacts, `__pycache__`, logs and local virtual environments.
- [ ] Check original-era Flash media permissions before distributing any complete-asset release.
- [ ] Prefer a **private repository** if third-party media permissions remain unclear.
