# Tyler Source Manifest

> Provenance/status: Tyler review/provenance artifact. Preserve for audit.
> Some status claims may be superseded by the current machine-readable
> registry. For current status, cross-check `docs/MAINTAINER_START_HERE.md`,
> `docs/tyler_requirements.yaml`, and
> `docs/tyler_requirements_registry.json`.

> Status: tracked-source reproducibility manifest for the raw Tyler packet.

The raw Tyler packet is tracked at `2026_0325_tyler_feedback/` even though the
directory remains in `.gitignore` to prevent accidental addition of unrelated
local feedback artifacts. These four files are the source text behind the
ledger line anchors.

| Source file | Lines | SHA-256 |
|---|---:|---|
| `2026_0325_tyler_feedback/1. V1_Build_Plan_Step_By_Step.md` | 248 | `962afd0e2fc9bce4c7aee81ede0b32a9797297b3a34d6270f8096ee57033f95a` |
| `2026_0325_tyler_feedback/2. V1_DESIGN.md` | 347 | `6c4f5c3e1ab631030da568a2a2b28e940a93de8a6eef172c9f332ba95f9125bb` |
| `2026_0325_tyler_feedback/3. V1_SCHEMAS.md` | 619 | `6c89eeffd1233d66e61d513dc6c0fa2b437a47beaf96fdc36eb1d0f9717d0881` |
| `2026_0325_tyler_feedback/4. V1_PROMPTS.md` | 1,163 | `d53aa8cb43267451848486b4de7b5425de5a751b08cdcbd7000f5e00b5befa41` |
| **Total** | **2,377** | |

Verify with:

```bash
make tyler-source-check
```
