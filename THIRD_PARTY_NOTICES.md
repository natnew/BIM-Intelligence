# Third-party notices

**Dependency inventory:** 31 October 2026. **Asset and evidence reconciliation:** 3 November
2026 on source baseline `588e6adf9ca71079eadc0e5b33422dc6605df743`; the dependency inventory
was not re-audited for a specific distributable.

## Purpose and scope

This inventory records the project licence, declared dependencies, relevant resolved package
metadata and third-party assets found in the repository. It distinguishes direct runtime packages,
development tools, transitive dependencies and assets copied into frontend builds. It is an
engineering inventory, not legal advice or a certification that every possible distribution
complies with every licence.

Python versions below are observations from the local development environment, not pinned
resolutions: `pyproject.toml` specifies ranges and the repository has no Python lockfile. The
frontend versions are resolved in [`frontend/package-lock.json`](./frontend/package-lock.json).
Package metadata and licence identifiers are not substitutes for reviewing the applicable licence
text and notices in a distribution-specific build.

## Project licence

The project is licensed under the [MIT License](./LICENSE), copyright (c) 2026 Natasha. Preserve
that notice in copies or substantial portions of the project's software. This notice does not
replace or amend the root licence.

## Python dependencies

Runtime and development requirements come from [`pyproject.toml`](./pyproject.toml). Versions in
the tables are those observed in the local `.venv` on the review date; they may differ in another
installation. Each package link is to its version-specific PyPI record.

### Direct runtime dependencies

| Component                                                               |                   Declared range | Observed version | Licence metadata                             |
| ----------------------------------------------------------------------- | -------------------------------: | ---------------: | -------------------------------------------- |
| [FastAPI](https://pypi.org/project/fastapi/0.162.0/)                    |                   `>=0.115,<1.0` |        `0.162.0` | MIT                                          |
| [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/)                     | `>=0.30,<1.0` (`standard` extra) |         `0.54.0` | BSD-3-Clause                                 |
| [Pydantic](https://pypi.org/project/pydantic/2.14.1/)                   |                     `>=2.7,<3.0` |         `2.14.1` | MIT                                          |
| [pydantic-settings](https://pypi.org/project/pydantic-settings/2.16.1/) |                     `>=2.7,<3.0` |         `2.16.1` | MIT                                          |
| [python-multipart](https://pypi.org/project/python-multipart/0.0.32/)   |                        `>=0.0.9` |         `0.0.32` | Apache-2.0                                   |
| [IfcOpenShell](https://pypi.org/project/ifcopenshell/0.9.0.post1/)      |                  `>=0.8.0,<0.10` |    `0.9.0.post1` | LGPL-3.0-or-later                            |
| [IfcTester](https://pypi.org/project/ifctester/0.9.0/)                  |                  `>=0.8.0,<0.10` |          `0.9.0` | LGPL-3.0-or-later (PyPI classifier: LGPLv3+) |
| [xmlschema](https://pypi.org/project/xmlschema/4.3.2/)                  |                     `>=3.0,<5.0` |          `4.3.2` | MIT                                          |
| [OpenAI Python SDK](https://pypi.org/project/openai/2.54.0/)            |                    `>=1.40,<3.0` |         `2.54.0` | Apache-2.0                                   |
| [pypdf](https://pypi.org/project/pypdf/6.21.2/)                         |                     `>=4.2,<7.0` |         `6.21.2` | BSD-3-Clause                                 |

### Direct development dependencies

| Component                                                | Declared minimum | Observed version | Licence metadata |
| -------------------------------------------------------- | ---------------: | ---------------: | ---------------- |
| [pytest](https://pypi.org/project/pytest/9.1.1/)         |          `>=8.2` |          `9.1.1` | MIT              |
| [pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/) |          `>=5.0` |          `7.1.0` | MIT              |
| [httpx](https://pypi.org/project/httpx/0.28.1/)          |         `>=0.27` |         `0.28.1` | BSD-3-Clause     |
| [ruff](https://pypi.org/project/ruff/0.17.3/)            |          `>=0.5` |         `0.17.3` | MIT              |
| [mypy](https://pypi.org/project/mypy/2.4.0/)             |         `>=1.10` |          `2.4.0` | MIT              |

### Build-system requirements

`setuptools>=69` and `wheel` are declared in the PEP 517 build-system requirements. Neither was
installed in the inspected `.venv`, so their resolved versions and licence metadata are
**UNVERIFIED**. A build may resolve them in an isolated environment; verify the actual build
environment before redistributing its contents.

### Python transitive dependencies and IFC-specific notes

Python transitive versions are not locked. The current local dependency graph includes
`bcf-client`, `odfpy`, `python-dateutil`, `numpy` and other packages pulled in by IfcTester and
other direct dependencies. Do not treat this local resolution as the complete or fixed inventory
for every supported installation.

| Component or asset          | Observed metadata and relationship                                                                                                                                                             | Licence/source status                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `bcf-client` `0.9.0`        | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **UNVERIFIED.** Its [PyPI 0.9.0 record](https://pypi.org/project/bcf-client/0.9.0/) has a GPLv3 classifier, while the [IfcOpenShell 0.9.0.post1 project description](https://pypi.org/project/ifcopenshell/0.9.0.post1/) lists the BCF library as LGPL-3.0-or-later. The PyPI record has no SPDX expression or licence file metadata. Resolve this upstream discrepancy and the applicable terms before redistributing an installed environment. |
| `odfpy` `1.4.1`             | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **UNVERIFIED.** Its installed metadata lists Apache, GPL and LGPL licence names without an SPDX expression or a clear selection. Verify the package's licence files and applicable grant before redistribution.                                                                                                                                                                                                                                  |
| `python-dateutil` `3.0.0`   | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **UNVERIFIED.** Installed metadata says `Dual License`; the exact licence choice was not established in this audit.                                                                                                                                                                                                                                                                                                                              |
| IDS 1.0 XSD (`ids.xsd`)     | IfcTester loads this schema from its installed package; first-party code references it but does not copy it into the repository. The schema declares version `1.0.0`.                          | The [buildingSMART IDS repository licence](https://github.com/buildingSMART/IDS/blob/development/LICENSE) identifies CC BY-ND 4.0 and buildingSMART International Ltd. The exact upstream revision corresponding to IfcTester's bundled copy is **UNVERIFIED**. The project does not modify the schema.                                                                                                                                          |
| IfcOpenShell wheel binaries | The inspected Windows wheel contains native DLLs, including Boost-named files. They are installed as part of the external IfcOpenShell dependency, not committed or copied by this repository. | The IfcOpenShell package declares LGPL-3.0-or-later. The licences and notices for every separately bundled native component in a redistributed wheel were not audited; verify them against the exact platform wheel before repackaging it.                                                                                                                                                                                                       |

The current repository imports IfcOpenShell and IfcTester. `bcf-client` is installed transitively
with IfcTester but no first-party BCF import was found. `ifcclash` is described as optional or
future functionality in existing documentation, is not declared in `pyproject.toml`, and is not
included as a current dependency in this inventory.

## Frontend dependencies

The frontend lockfile is npm lockfile version 3. It records exact versions and a `license` field for
all 221 package records, including nested and platform-specific optional packages. The following
tables list the 22 direct dependencies; the remaining lockfile records are transitive dependencies.
Npm package links expose the corresponding package metadata.

### Direct runtime dependencies

| Component                                                                                      | Resolved version | Licence field |
| ---------------------------------------------------------------------------------------------- | ---------------: | ------------- |
| [@thatopen/components](https://www.npmjs.com/package/@thatopen/components/v/3.6.0)             |          `3.6.0` | MIT           |
| [@thatopen/components-front](https://www.npmjs.com/package/@thatopen/components-front/v/3.6.0) |          `3.6.0` | MIT           |
| [@thatopen/fragments](https://www.npmjs.com/package/@thatopen/fragments/v/3.6.0)               |          `3.6.0` | MIT           |
| [React](https://www.npmjs.com/package/react/v/19.3.1)                                          |         `19.3.1` | MIT           |
| [React DOM](https://www.npmjs.com/package/react-dom/v/19.3.1)                                  |         `19.3.1` | MIT           |
| [Three.js](https://www.npmjs.com/package/three/v/0.182.0)                                      |        `0.182.0` | MIT           |
| [web-ifc](https://www.npmjs.com/package/web-ifc/v/0.0.77)                                      |         `0.0.77` | MPL-2.0       |

### Direct development dependencies

| Component                                                                                         | Resolved version | Licence field |
| ------------------------------------------------------------------------------------------------- | ---------------: | ------------- |
| [@testing-library/jest-dom](https://www.npmjs.com/package/@testing-library/jest-dom/v/7.0.1)      |          `7.0.1` | MIT           |
| [@testing-library/react](https://www.npmjs.com/package/@testing-library/react/v/16.3.3)           |         `16.3.3` | MIT           |
| [@testing-library/user-event](https://www.npmjs.com/package/@testing-library/user-event/v/14.6.8) |         `14.6.8` | MIT           |
| [@types/node](https://www.npmjs.com/package/@types/node/v/24.19.2)                                |        `24.19.2` | MIT           |
| [@types/react](https://www.npmjs.com/package/@types/react/v/19.3.0)                               |         `19.3.0` | MIT           |
| [@types/react-dom](https://www.npmjs.com/package/@types/react-dom/v/19.3.0)                       |         `19.3.0` | MIT           |
| [@types/three](https://www.npmjs.com/package/@types/three/v/0.182.0)                              |        `0.182.0` | MIT           |
| [@vitejs/plugin-react](https://www.npmjs.com/package/@vitejs/plugin-react/v/6.1.2)                |          `6.1.2` | MIT           |
| [jsdom](https://www.npmjs.com/package/jsdom/v/30.1.3)                                             |         `30.1.3` | MIT           |
| [json-schema-to-typescript](https://www.npmjs.com/package/json-schema-to-typescript/v/16.0.0)     |         `16.0.0` | MIT           |
| [oxlint](https://www.npmjs.com/package/oxlint/v/1.90.0)                                           |         `1.90.0` | MIT           |
| [Prettier](https://www.npmjs.com/package/prettier/v/3.9.10)                                       |         `3.9.10` | MIT           |
| [TypeScript](https://www.npmjs.com/package/typescript/v/7.0.2)                                    |          `7.0.2` | Apache-2.0    |
| [Vite](https://www.npmjs.com/package/vite/v/8.3.5)                                                |          `8.3.5` | MIT           |
| [Vitest](https://www.npmjs.com/package/vitest/v/5.0.5)                                            |          `5.0.5` | MIT           |

### Notable transitive frontend licences

The licence fields below are copied into the lockfile from package metadata. They are useful
identifiers, not an independent review of every package's licence text. Exact package names,
versions and fields for the full graph are in
[`frontend/package-lock.json`](./frontend/package-lock.json).

| Component(s)                                                                           | Scope and recorded licence                                                              | Consideration                                                                                                                            |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `lightningcss` `1.33.0` and its 11 platform packages                                   | Development tooling; MPL-2.0                                                            | These are lockfile records for build tooling, not files intentionally copied to the browser bundle.                                      |
| `jszip` `3.10.1`                                                                       | Runtime transitive package; `(MIT OR GPL-3.0-or-later)`                                 | This is an alternative licence expression. Confirm the selected grant and retain its applicable notices when redistributing the package. |
| `pako` `2.1.0` and nested `pako` `1.0.11`                                              | Runtime transitive packages; `(MIT AND Zlib)` and `(MIT AND Zlib)`                      | The expression is conjunctive; retain both applicable notices.                                                                           |
| `argparse` `3.0.4`; nested `argparse` `2.0.1`                                          | Development tooling; PSF-2.0 and Python-2.0                                             | Preserve the respective upstream licence notices if these packages are redistributed.                                                    |
| `lru-cache` `11.5.3`; `mdn-data` `2.27.1`                                              | Development tooling; BlueOak-1.0.0 and CC0-1.0                                          | Retain the package metadata and review upstream terms for the distribution form.                                                         |
| `@csstools/color-helpers` `6.1.2`; `@csstools/css-syntax-patches-for-csstree` `1.1.15` | Development tooling; MIT-0                                                              | MIT-0 does not impose the MIT notice condition; do not relabel it as MIT.                                                                |
| ISC/BSD transitive packages                                                            | The lockfile records five ISC, three BSD-3-Clause and two BSD-2-Clause package records. | The full names and versions are listed in the lockfile; preserve required notices if redistributing those packages.                      |

The lockfile contains 162 MIT, 27 Apache-2.0, 13 MPL-2.0 and 19 other licence-field records. Those
counts include nested and platform-specific packages and are not counts of unique software projects.
These are package metadata declarations rather than a legal review of the distribution.

## Attribution and redistribution obligations

- **MIT, BSD and ISC:** retain the applicable copyright, licence and disclaimer notices when
  redistributing covered package code. The root MIT notice covers this project's code; it does not
  replace dependency notices.
- **Apache-2.0:** include the licence text and preserve any upstream `NOTICE` file when
  redistributing covered components.
- **LGPL-3.0-or-later:** IfcOpenShell and IfcTester declare this licence. If redistributing these
  libraries or a combined work, include the applicable licence and notices and meet the relevant
  source and user-replacement/relinking requirements. The precise requirements depend on the
  distribution and linking form; review the exact package and platform wheel before bundling it.
- **MPL-2.0:** web-ifc declares this licence and its npm package includes `LICENSE.md`. For a
  redistributed frontend containing its WASM or JavaScript, include a copy of the licence or an
  accessible licence URL and meet the applicable source-availability and notice requirements in
  [MPL-2.0 sections 3.1-3.2](https://www.mozilla.org/en-US/MPL/2.0/). Review the generated
  distribution form; no web-ifc source or binary is committed here.
- **CC BY-ND 4.0:** the upstream IDS repository requires attribution and a licence reference for
  covered material; do not distribute an adapted version under that grant. Verify the provenance
  and licence of IfcTester's exact bundled schema before copying or redistributing it separately.
- **Alternative or compound expressions:** package metadata records `jszip` as
  `(MIT OR GPL-3.0-or-later)` and `pako` as `(MIT AND Zlib)`. Verify the applicable choice or both
  required grants and preserve the corresponding notices. The `bcf-client` licence conflict and
  `odfpy`/`python-dateutil` metadata must be resolved before redistributing a Python environment.

## Assets and redistribution

| Asset or component                                                                                       | Repository/build status                                                                                                                                                                                                                             | Attribution and verification                                                                                                                                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`assets/BIM-Intelligence Architectural Logo.png`](./assets/BIM-Intelligence%20Architectural%20Logo.png) | Tracked image.                                                                                                                                                                                                                                      | **UNVERIFIED:** the repository does not establish its creator, source or redistribution licence. Confirm ownership or permission before redistributing it.                                                                                                                                                                                                                                            |
| [`assets/bim-intelligence-panel.png`](./assets/bim-intelligence-panel.png)                               | Tracked application-panel image.                                                                                                                                                                                                                    | **UNVERIFIED:** the repository does not record its creator, source or redistribution licence. Confirm the image and any content within it are rights-cleared before redistributing it.                                                                                                                                                                                                                |
| [`frontend/public/favicon.svg`](./frontend/public/favicon.svg)                                           | Tracked SVG icon.                                                                                                                                                                                                                                   | **UNVERIFIED:** no author or licence notice is present. Confirm its provenance and redistribution rights.                                                                                                                                                                                                                                                                                             |
| [`frontend/public/images/home/bim-intelligence-hero.webp`](./frontend/public/images/home/bim-intelligence-hero.webp) | Tracked Project Home banner, optimised from an owner-supplied image. | The owner confirmed public redistribution rights for the banner on 2 November 2026. This is an owner-reported permission, not an independent legal assessment. |
| [`frontend/public/images/home/reel/`](./frontend/public/images/home/reel/) | Six tracked architectural scene images, including a labelled concept visualisation. | For UI-005D the owner identified the images as AI-generated and confirmed public redistribution and optimised-derivative rights. Do not present the concept as an application screenshot. |
| [`docs/assets/research/`](./docs/assets/research/) | Two tracked, owner-supplied research graphics in the README. | The UI-005D review records the owner's redistribution and derivative permission. The graphics cite Autodesk, Springer Nature Link and RICS, but their numerical claims and underlying sources have not been independently checked; permission for the graphics is not verification of the statistics. |
| [`examples/`](./examples/) | Tracked collection descriptions, draft IDS files, two spreadsheets and four images; no IFC models are tracked there. | **UNVERIFIED:** individual sources, licences, redistribution rights and applicability. Collection notes contain licence assertions that have not been independently verified. Review each tracked non-IFC asset and its contents before publication; do not infer rights from availability or a filename. |
| [`tests/fixtures/minimal.ifc`](./tests/fixtures/minimal.ifc) and [`minimal.ids`](./tests/fixtures/minimal.ids) | Tracked, synthetic three-wall IFC4 and IDS fixtures generated by [`make_minimal_ifc.py`](./tests/fixtures/make_minimal_ifc.py); not an external project model. | Project-authored test inputs under the repository [MIT licence](./LICENSE). The fixture references the third-party Uniclass 2015 system and one code, not a redistributed classification catalogue; confirm any applicable attribution or terms before redistribution. No external example model is included or cleared by this entry. |
| `web-ifc.wasm` and `web-ifc-mt.wasm`                                                                     | Not tracked. `frontend/scripts/copy-wasm-assets.mjs` copies both files from the locked `web-ifc` package into the ignored `frontend/public/web-ifc/` directory for development and builds; the frontend build can include them in `frontend/dist/`. | The source package is `web-ifc` `0.0.77`, which declares MPL-2.0 and ships `LICENSE.md` in its npm package. For any distribution of the generated frontend, include the applicable MPL licence text or an accessible licence URL and meet the source/notice obligations in [MPL-2.0 sections 3.1-3.2](https://www.mozilla.org/en-US/MPL/2.0/). The exact obligations depend on the distribution form. |
| IfcOpenShell native wheel contents                                                                       | Installed by Python dependency resolution; not tracked or copied by this repository. The inspected Windows wheel contains native DLLs.                                                                                                              | The package declares LGPL-3.0-or-later; separate licences/notices for all bundled native components were not independently verified. Do not treat this repository's source inventory as a complete notice bundle for a repackaged wheel.                                                                                                                                                              |

No third-party JavaScript, WebAssembly, font or native binary files are tracked in the repository.
No external font or asset-hosting references were found in the frontend source examined for this
audit. Built frontend output and copied web-ifc assets are ignored by Git and are not evidence that
the project has published a distribution.

The IDS schema is a separate attribution consideration: the upstream buildingSMART IDS repository
identifies buildingSMART International Ltd. and CC BY-ND 4.0. If the schema is ever copied or
redistributed independently, preserve the required attribution and licence reference, do not
distribute an adapted version under that grant, and first verify the exact provenance of the copy.

## Verification limits and follow-up

- The Python project has no lockfile. Re-run a licence and notice inventory against the exact
  dependency resolution and target platform used for each distributable.
- The `bcf-client` licence conflict, `odfpy` grant, `python-dateutil` dual-licence choice, build
  tool metadata, bundled IfcOpenShell native components, logo/panel/favicon provenance and
  tracked example-asset rights remain **UNVERIFIED** as described above. The research graphics'
  numerical claims and underlying source citations also need independent verification.
- The npm lockfile records licence fields for all package records, but this audit did not unpack
  and compare every transitive package's `LICENSE`/`NOTICE` file. Validate those files for a
  concrete redistribution.
- No full third-party licence texts are reproduced here. Follow the distribution-specific terms
  above and include upstream licence texts or notices where required.

Authoritative licence texts: [MIT](https://spdx.org/licenses/MIT.html),
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0),
[LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html),
[MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/),
[CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/),
[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html),
[BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html),
[BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html),
[ISC](https://spdx.org/licenses/ISC.html),
[PSF-2.0](https://spdx.org/licenses/PSF-2.0.html),
[Python-2.0](https://spdx.org/licenses/Python-2.0.html),
[BlueOak-1.0.0](https://spdx.org/licenses/BlueOak-1.0.0.html),
[CC0-1.0](https://spdx.org/licenses/CC0-1.0.html),
[MIT-0](https://spdx.org/licenses/MIT-0.html) and
[Zlib](https://spdx.org/licenses/Zlib.html). The applicable package licence and any accompanying
notices take precedence over this summary.
