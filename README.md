# NGK14 — 14‑pixel Rockbox Font that supports Japanese and Korean characters

**NGK14** is a compact bitmap font set for Rockbox, built by merging:

- **Nimbus14** (from the Rockbox repository)
- **Galmuri11** (SIL OFL‑1.1)
- **JIS X 0213 k12** (Public Domain, Imamura)

Two versions are provided:

- `NGK14`: normal
- `NGK14‑padded`: Nimbus14 with a small header patch applied for slightly different spacing

All fonts are generated from BDF sources using `bdf_merge.py` and converted to Rockbox `.fnt` via `convbdf`.

---

## Building

Make sure you have a local Rockbox tools build (for `convbdf`).

```bash
export ROCKBOX_TOOLS=/path/to/rockbox/tools
make
```

This produces:

```
dist/bdf/NGK14-14.bdf
dist/rockbox/14-NGK14.fnt
dist/bdf/NGK14-padded-14.bdf
dist/rockbox/14-NGK14-padded.fnt
```

---

## Using with the *Flattery* Theme

The font is designed for the [**Flattery**](https://themes.rockbox.org/index.php?themeid=3462)[ theme](https://themes.rockbox.org/index.php?themeid=3462) — an iPodOS‑style skin for Rockbox.

You can install NGK14 in one of two ways:

### Option A — Replace existing Nimbus

1. Build the font as above.
2. Backup the originals if present:
   ```
   /.rockbox/fonts/14-Nimbus.fnt
   /.rockbox/fonts/14-Nimbus-padded.fnt
   ```
3. Copy the resulting `.fnt` files to your player:
```
/.rockbox/fonts/14-NGK14.fnt
/.rockbox/fonts/14-NGK14-padded.fnt
```
4. Rename the new fonts to match:
   ```
   14-NGK14.fnt → 14-Nimbus.fnt
   14-NGK14-padded.fnt → 14-Nimbus-padded.fnt
   ```
5. Reload the theme from Rockbox settings.

This method makes Flattery use NGK14 automatically without editing any theme files.

### Option B — Update the theme manually

If you prefer not to rename fonts, edit the theme. 

<img width="1521" height="533" alt="image" src="https://github.com/user-attachments/assets/63c133dd-7aea-427e-86e2-13f49d053445" />

---

## Licensing

- **Galmuri11** — SIL Open Font License 1.1
- **JIS X 0213 k12** — Public Domain
- **Nimbus14** — from the Rockbox repository (no explicit license; treated as public domain bitmap)

See `LICENSES/` for details.

