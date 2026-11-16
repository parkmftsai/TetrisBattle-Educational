# Original-era asset integration: background and limits

Assets were inspected from the user-supplied archive corresponding to [greenspiritcompany/tetrisfb-assets](https://github.com/greenspiritcompany/tetrisfb-assets). Important source files included `data1.81.0/flash/binary/FacebookMainframe.swf` and localized XML message tables. The SWF contained 54 named sound definitions. Original-era sounds such as `FX_COMBO01`–`FX_COMBO07`, `FX_BOMB01a`–`FX_BOMB04a`, `FX_TSPIN`, `FX_HRDDP` and line-clearing cues were mapped into an optional Pygame sound pack. Combo 8–10 reuse the highest available original voice cue; they are **not** three extra originals.

Phase 1 visuals include selected Classic, Default and Neon minos, three ghost styles, three bomb styles and animation frames reconstructed from vector elements. The visual effects are not exact exports of the historical Flash timeline. The assets are optional; missing files should fall back to bundled artwork.

## Rebuild from a separately obtained authorized source

Rebuilding source-derived audio uses FFmpeg. Only use source files and clips for which you have appropriate rights.

```bash
python tools/extract_fb_swf_audio.py --source-zip path/to/your-authorized-archive.zip --activate --overwrite
```

You can import your own authorized gameplay recording with `tools/import_recorded_sfx.py` and an appropriately documented cue sheet.

**Copyright:** Public access to an archive is not a grant of rights to copy or republish its media. The repository provides source attribution, not a claim of permission. See `NOTICE.md` and use a private GitHub repository for the complete media-containing version unless permissions are confirmed.
