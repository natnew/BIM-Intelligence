# BIM Intelligence — Example IFC Project
This library describes three example-project collections for exploring IFC models and evaluating

This library describes intended example-project collections for exploring IFC models and evaluating

BIM Intelligence. Architects can inspect geometry and elements; BIM Managers and BIM Coordinators
can examine model information against project requirements; developers can assess ingestion, viewing
and performance.


The owner keeps local copies of the IFC models in each collection directory. Git ignores `*.ifc`
files under `examples/`, so the models are not tracked or published with the repository. This is
not an implemented example catalogue, and one-click example loading is not available.

Other file types, such as spreadsheets, images, PDFs and IDS files, are not covered by the IFC
ignore rule and may be visible to Git. Keep private or rights-uncleared inputs in `local-private/`
and check their status before publication.

## Project collections

| Collection | Disciplines suggested by filenames | Intended evaluation | Expected IFC inputs | Benchmark IDS |
|---|---|---|---|---|
| [Duplex Apartment](./duplex-apartment/README.md) | Architectural, electrical, mechanical/MEP and plumbing; rooms and spaces | Model and property inspection, IDS validation, future multidisciplinary coordination | `Duplex_A_20110907.ifc`, `Duplex_Electrical_20121207.ifc`, `Duplex_M_20111024_ROOMS_AND_SPACES.ifc`, `Duplex_MEP_20110907.ifc`, `Duplex_Plumbing_20121113.ifc` | [Draft](./duplex-apartment/benchmark.ids) |
| [Medical Dental Clinic](./medical-dental-clinic/README.md) | Architectural, structural, HVAC, electrical and plumbing | Geometry, navigation, rendering, project-specific IDS validation, future multidisciplinary coordination | `Clinic_Architectural.ifc`, `Clinic_Electrical.ifc`, `Clinic_HVAC.ifc`, `Clinic_Plumbing.ifc`, `Clinic_Structural.ifc` | [Draft](./medical-dental-clinic/benchmark.ids) |
| [Molio](./molio/README.md) | To be confirmed; information and reference example | Metadata, properties, references and IDS validation against an applicable specification | `Molio_with_URIs.ifc` | [Draft](./molio/benchmark.ids) |

The disciplines are taken from the file names and collection notes, not from verified model
contents. The Medical Dental Clinic README records a CC BY 4.0 licence statement and attribution
requirement from its source. **Source URLs, licences and redistribution rights for every
collection, file hashes, IFC versions, IDS applicability and application compatibility:**
**Pending verification.**

## Exploratory benchmark drafts

Each collection contains a `benchmark.ids` with generic candidate checks based on the synthetic
benchmark's IDS format. The Duplex and Clinic drafts propose checking names and GlobalIds for
projects, storeys, spaces and a limited selection of building and services elements. The Molio
draft proposes project and element identity checks and a classification-reference location check;
the latter checks presence only, not whether a URI is valid or reachable.

These are **draft examples, not verified or approved project requirements**. They were not derived
from, or run against, the collection models. Their applicability, coverage and results remain
unverified; no ground truth, accuracy or compliance claim is implied. Entity selectors cover only
the listed IFC classes, not every possible class or subtype.

The owner must review, edit and approve each specification before importing it: the application
treats imported IDS specifications as confirmed. Each session contains one IFC, so checks for
entities absent from that file can be reported as not applicable and the review can be partial.

The collections currently contain descriptions only. They are not an implemented example
catalogue, and one-click example loading is not available.

## Project collections

| Collection | Expected disciplines | Intended evaluation |
|---|---|---|
| [Duplex Apartment](./duplex-apartment/README.md) | Architectural, electrical, mechanical/MEP and plumbing; rooms and spaces | Model and property inspection, IDS validation, and future multidisciplinary coordination |
| [Medical Dental Clinic](./medical-dental-clinic/README.md) | Architectural | Geometry, navigation, rendering and project-specific IDS validation |
| [Molio](./molio/README.md) | To be confirmed; information and reference example | Metadata, properties, references and applicable information-quality checks |
| [Schependomlaan](./schependomlaan/README.md) | Architectural | Ingestion, viewer robustness, information inspection, performance and future coordination |

These are intended inputs and uses, not verified descriptions of model contents.
**Availability, source URLs, licences and redistribution rights, file hashes, IFC versions and
application compatibility:** **Pending verification.**


## Exploration and information-quality review

An Industry Foundation Classes (IFC) file exchanges a BIM model and its available geometry and
information. Exploring a model means navigating it and inspecting its elements and properties; this
does not execute checks or establish compliance.

A buildingSMART Information Delivery Specification (IDS) expresses machine-readable requirements
for IFC information. An IDS is optional for visual exploration but is necessary to validate a
model against project-specific IDS requirements. A deterministic review requires at least one
confirmed executable requirement. Imported IDS specifications are treated as confirmed, so review
their suitability before importing them; check the resulting coverage and any partial or error
status.

The current application has one active IFC model per session. Model federation and geometric clash
detection are not integrated into the application; geometric clash detection requires a separate
implemented coordination capability. The synthetic feasibility harness is not that capability.
Uploaded IFC bytes remain unchanged: the application does not modify or re-save the source model
during evaluation.

## Storage and licensing

| Location | Purpose |
|---|---|

| `examples/<collection>/` | Project descriptions, draft IDS inputs, future catalogue manifests and the owner's local, Git-ignored copies of the example IFC models |

| `examples/` | Project descriptions and future catalogue manifests, not model storage |

| `local-private/bim-models/<collection>/` | Owner-managed IFC files for local evaluation, including private or not-yet-cleared inputs |
| `local-private/bim-documents/<collection>/` | Associated private or not-yet-cleared IDS files and supporting documents |
| `datasets/permitted/<collection>/` | Openly licensed sample IFC files and associated evaluation assets verified for redistribution |
| `datasets/synthetic/` | Synthetic benchmark material, kept separate from these examples |
| `tests/fixtures/` | Small deterministic regression fixtures, not a project library |

Use the collection directory names shown above for `<collection>`. The owner can create the private
or permitted input directories when adding actual files; they are not created by this library.
Never commit real project models, private inputs or material derived from `hackathon-private/`.
Git ignore rules are not access controls.

Before publication, verify the authoritative source, licence, redistribution permission and
required attribution for each IFC, IDS and supporting asset. Record the source URL and applicable
licence text per file in `datasets/permitted/LICENCES.md`, creating it when permitted files are
added. The [dataset policy](../datasets/README.md) prohibits committing files larger than
approximately 5 MB. This is separate from the configurable application upload limits, which
default to 200 MiB for IFC (`MAX_IFC_MB`) and 25 MiB for documents such as IDS (`MAX_DOC_MB`).
Being within an upload limit does not grant permission to publish a file.

Follow the [private-data and provenance rules](../AGENTS.md#private-data-handling-and-provenance).
Local access or inspection does not authorise transmission to an LLM service: explicit owner
approval and applicable data rights are required. Changes involving private-data handling also
require the documented security and provenance review.

## Open a model and import an IDS

1. Once use is authorised, place an IFC and any separately prepared IDS in the appropriate
   collection locations above. Verify the source and licence before considering redistribution.
2. Start the backend and frontend using the [local setup](../README.md#local-setup), then open the
   application in a browser.
3. On Project Home, under **New review**, select **Create review session**. Use **Choose IFC model**
   to upload one existing `.ifc` file.
4. For project-specific IDS validation, use **Add requirements document** to import an applicable,
   reviewed `.ids` file. This can also be done in the workspace. Skip this step for visual
   exploration only.
5. Select **Open review workspace**. Inspect the model; if executable requirements are present,
   select **Run review** and inspect the findings and coverage.

The application stores an uploaded copy under its configured data directory; it does not change the
original IFC. A model view or an absence of findings is not, on its own, evidence of complete
review coverage.
