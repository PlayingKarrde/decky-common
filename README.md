# decky-common

Code shared by two Decky Loader plugins, [gameyfin-decky](https://github.com/PlayingKarrde/gameyfin-decky) and [romm-decky](https://github.com/PlayingKarrde/romm-decky).

Each plugin keeps a **committed copy** of this repo, made by `sync.sh`. A plugin zip has to be self-contained, and each plugin can stay on an older version until it's ready to move. Nothing here is loaded at runtime from this repo.

## What's here

Only code that knows nothing about Gameyfin or RomM. Anything tied to one source stays in that plugin: install logic, the API clients, the library UI, the job and state format, pairing.

| Here | Copied to | What |
|---|---|---|
| `deckycommon/net.py` | `py_modules/<pkg>/common/` | CA bundle (`ssl_context`, `urlopen`), User-Agent, `PluginError`, `Image` |
| `deckycommon/images.py` | ditto | On-disk image cache that feeds images through the ~1 MiB bridge in chunks |
| `deckycommon/sgdb.py` | ditto | SteamGridDB client, id resolution, `art_plan` |
| `deckycommon/selfupdate.py` | ditto | Checks GitHub releases (`Updater(repo, asset_prefix)`) |
| `deckycommon/phoneform.py` | ditto | Short-lived LAN page where a phone sends a token or key (`PhoneForm`, `shell`, `sgdb_section`) |
| `ts/Cover.tsx` | `src/common/` | Cover image component with a thumbnail cache |
| `ts/artwork.ts` | `src/common/` | `applyArtwork(appId, plan)`: Steam capsule, wide, hero and logo |
| `ts/ArtworkPanel.tsx` | `src/common/` | QAM section for the SteamGridDB key and square covers; phone flow optional |
| `ts/PhoneModal.tsx` | `src/common/` | QR code and status for a `PhoneForm`; backend calls passed as props |
| `scripts/cdp.py` | `scripts/cdp.py` | Runs JS in the Deck's SharedJSContext; `call()` targets the plugin named in `plugin.json` |

## Contracts with the plugin

- **Python:** imports inside the package are relative, so it works as `<pkg>.common`.
  - The plugin's `client.py` aliases the error type (`GameyfinError = PluginError`, not a subclass), so its own `except` catches errors raised here.
  - It also calls `net.set_user_agent(...)`.
- **TypeScript:** files import `../backend` (except `PhoneModal`, which takes its calls as props), which resolves to the plugin's `src/backend.ts`. The exports each file needs are listed at its top. Each plugin's `pnpm typecheck` enforces this.

## Workflow

1. Change the code here, run `python3 -m unittest discover -s tests`, and commit.
2. In each plugin, run `scripts/sync-common.sh` (it calls `../decky-common/sync.sh`). Then typecheck, test and commit there.
   - The plugin's `.decky-common` file records the commit its copies came from.
   - Plugin CI checks out that commit, re-syncs, and fails if the copies differ.
3. Never edit the copies inside a plugin. Change them here and sync.

Push a commit here before pushing a plugin that records it, or that plugin's CI can't check it out.
