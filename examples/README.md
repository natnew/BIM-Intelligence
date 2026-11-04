# Example projects

These collections describe public sample projects for exploring IFC models in BIM Intelligence and
trying information-quality checks on them. Architects can inspect geometry and elements; BIM
managers and coordinators can check model information against requirements; developers can test
ingestion, viewing and performance.

The IFC models themselves are **not included**. The repository ignores `*.ifc` files outside the
test fixtures and synthetic datasets, so download each model from its source and place it in the
collection folder. There is no one-click example loader yet.

## Collections

| Collection | Disciplines | Included in the repository | Draft IDS |
|---|---|---|---|
| [Duplex Apartment](./duplex-apartment/README.md) | Architectural, electrical, mechanical, plumbing; rooms and spaces | Description, two COBie spreadsheets and four discipline drawings | [`benchmark.ids`](./duplex-apartment/benchmark.ids) |
| [Medical-Dental Clinic](./medical-dental-clinic/README.md) | Architectural, structural, HVAC, electrical, plumbing | Description | [`benchmark.ids`](./medical-dental-clinic/benchmark.ids) |
| [Molio](./molio/README.md) | Information and classification reference example | Description and buildingSMART's [`Molio_Example.ids`](./molio/Molio_Example.ids) | [`benchmark.ids`](./molio/benchmark.ids) |

Each collection README lists the expected IFC file names. The disciplines come from those file
names and the source descriptions; the model contents have not been checked file by file.

## Sources and licences

- **Duplex Apartment** and **Medical-Dental Clinic** are test files published by buildingSMART
  International under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). They were
  originally hosted by the US National Institute of Building Sciences. Credit them as
  BSI (2020) "Duplex Apartment Test Files" or "Medical-Dental Test Files", buildingSMART
  International.
- **Molio:** `Molio_Example.ids` records buildingSMART as its copyright holder; the buildingSMART
  [IDS repository](https://github.com/buildingSMART/IDS) is licensed
  [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/).
- The `benchmark.ids` files were written for this project and are covered by the project's
  [MIT License](../LICENSE).

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for the full attribution details. Check
each source's current licence before redistributing a model.

## Draft benchmark IDS files

Each collection has a `benchmark.ids` with generic candidate checks in the same format as the
synthetic benchmark:

- **Duplex Apartment and Medical-Dental Clinic:** names and GlobalIds for the project, storeys,
  spaces and a selection of building and services elements.
- **Molio:** project and element identity, and whether a classification reference is present (it
  does not check that a URI is valid or reachable).

These are **drafts, not project requirements**. They have not been run against the collection
models, and no accuracy or compliance result is claimed for them. Each specification covers only
the IFC classes it lists.

The application treats every imported IDS specification as confirmed, so review and edit a draft
before importing it. A session holds one IFC model, so checks for entity types that are absent from
that model are reported as not applicable and the review is marked partial.

## Exploring a model and running a review

An IFC file carries a BIM model's geometry and information. Exploring a model, by navigating it and
inspecting elements and properties, does not run any checks. An Information Delivery Specification
(IDS) expresses machine-readable information requirements; you need one, or the built-in
classification-consistency rule, to run a review.

1. Download a model from its source and place it in the collection folder.
2. Start the backend and frontend as described in the README [Quick start](../README.md#quick-start),
   then open the application.
3. On Project Home, choose **Create review session**, then **Choose IFC model** and upload the
   `.ifc` file.
4. To check the model against requirements, use **Add requirements document** to import a reviewed
   `.ids` file. Skip this step if you only want to explore the model.
5. Choose **Open review workspace**. Inspect the model and, if requirements are present, choose
   **Run AI Review** (or **Continue without AI**) and inspect the findings and coverage.

The application stores its own copy of the upload and never changes the original IFC. A model view,
or an empty findings list, is not evidence that a model is complete or compliant.

## Storage

| Location | Purpose |
|---|---|
| `examples/<collection>/` | Collection descriptions, draft IDS files, and your local, git-ignored copies of the example models |
| `datasets/synthetic/` | Synthetic benchmark material, generated on demand |
| `datasets/permitted/` | Openly licensed sample models cleared for redistribution (not used yet) |
| `tests/fixtures/` | Small deterministic regression fixtures |

The [dataset policy](../datasets/README.md) does not allow committed files larger than about 5 MB.
That is separate from the application's upload limits, which default to 200 MB for IFC models
(`MAX_IFC_MB`) and 25 MB for documents (`MAX_DOC_MB`).

Never commit real project models or private documents; keep them outside the repository. Only send
model data to a provider if you have the right to share it. See the
[private-data rules](../AGENTS.md#private-data-handling-and-provenance).
