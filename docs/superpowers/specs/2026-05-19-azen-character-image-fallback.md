# AZEN Character Image Fallback

## Goal

Allow AZEN character entries to resolve their character image assets from `data/a000` when the normal `ddsImage` manifest path is not present under the pack directory.

## Scope

This change covers:

- Scan-time character image resolution for characters sourced from the `AZEN` pack
- A fallback lookup under `data/a000` only after the normal `ddsImage` manifest lookup fails
- Preserving the existing character image endpoint contract once a valid image path is found

This change does not cover:

- Changing image resolution rules for non-`AZEN` packs
- Broadening file access outside the selected game root
- Changing browser-side thumbnail fallback behavior
- Introducing new manifest formats beyond the paths already proven in the game files

## Current State

- Character image resolution normally follows the pack-local `ddsImage/.../DDSImage.xml` manifest path.
- Some `AZEN` character XML files exist without a matching manifest in the pack-local `ddsImage` directory.
- For those characters, the actual DDS image files can live under `data/a000`, so the current scanner leaves `imageUrl` and `imageThumbUrl` empty even though usable assets exist.

## Recommended Approach

Keep the existing manifest-first behavior, and add a narrow `AZEN`-only fallback:

1. Attempt the current pack-local `ddsImage` manifest lookup first.
2. If the character came from `AZEN` and that manifest path does not exist, look for the same manifest-driven asset under `data/a000`.
3. Reuse the existing validation and safe-path checks before returning any resolved image path.
4. Leave unresolved characters unchanged when neither location contains a valid image asset.

This keeps responsibilities clear:

- `scanner.py` remains the only place that knows how character image paths are discovered.
- `server.py` and `image_utils.py` continue serving and converting resolved paths without AZEN-specific logic.
- The UI remains unchanged because it already consumes `imageUrl` and `imageThumbUrl` from scan output.

## Validation

- Confirm an `AZEN` character with no pack-local `ddsImage` manifest resolves an image from `data/a000`.
- Confirm an `AZEN` character with a valid pack-local manifest still prefers the original location.
- Confirm non-`AZEN` characters do not search `data/a000`.
- Confirm unresolved `AZEN` characters still return empty image fields instead of unsafe paths.
