# Third-party notices

Last reviewed: 4 November 2026.

## Purpose and scope

This file lists the project licence, the declared dependencies and their licences, and the
images and example files included in the repository. It is an engineering inventory, not legal
advice.

Python versions below are the versions resolved by a fresh install on the review date, not pinned
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
the tables were resolved by `pip install -e ".[dev]"` on Python 3.12 on the review date; another
installation may resolve different versions within the declared ranges. Each package link is to its version-specific PyPI record.

### Direct runtime dependencies

| Component                                                               |                   Declared range | Resolved version | Licence metadata                             |
| ----------------------------------------------------------------------- | -------------------------------: | ---------------: | -------------------------------------------- |
| [FastAPI](https://pypi.org/project/fastapi/0.162.0/)                    |                   `>=0.115,<1.0` |        `0.162.0` | MIT                                          |
| [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/)                     | `>=0.30,<1.0` (`standard` extra) |         `0.54.0` | BSD-3-Clause                                 |
| [Pydantic](https://pypi.org/project/pydantic/2.14.2/)                   |                     `>=2.7,<3.0` |         `2.14.2` | MIT                                          |
| [pydantic-settings](https://pypi.org/project/pydantic-settings/2.16.2/) |                     `>=2.7,<3.0` |         `2.16.2` | MIT                                          |
| [python-multipart](https://pypi.org/project/python-multipart/0.0.33/)   |                        `>=0.0.9` |         `0.0.33` | Apache-2.0                                   |
| [IfcOpenShell](https://pypi.org/project/ifcopenshell/0.9.0.post1/)      |                  `>=0.8.0,<0.10` |    `0.9.0.post1` | LGPL-3.0-or-later                            |
| [IfcTester](https://pypi.org/project/ifctester/0.9.0/)                  |                  `>=0.8.0,<0.10` |          `0.9.0` | LGPL-3.0-or-later (PyPI classifier: LGPLv3+) |
| [xmlschema](https://pypi.org/project/xmlschema/4.3.2/)                  |                     `>=3.0,<5.0` |          `4.3.2` | MIT                                          |
| [OpenAI Python SDK](https://pypi.org/project/openai/2.54.0/)            |                    `>=1.40,<3.0` |         `2.54.0` | Apache-2.0                                   |
| [pypdf](https://pypi.org/project/pypdf/6.21.4/)                         |                     `>=4.2,<7.0` |         `6.21.4` | BSD-3-Clause                                 |

### Direct development dependencies

| Component                                                | Declared minimum | Resolved version | Licence metadata |
| -------------------------------------------------------- | ---------------: | ---------------: | ---------------- |
| [pytest](https://pypi.org/project/pytest/9.2.0/)         |          `>=8.2` |          `9.2.0` | MIT              |
| [pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/) |          `>=5.0` |          `7.1.0` | MIT              |
| [httpx](https://pypi.org/project/httpx/0.28.1/)          |         `>=0.27` |         `0.28.1` | BSD-3-Clause     |
| [ruff](https://pypi.org/project/ruff/0.17.3/)            |          `>=0.5` |         `0.17.3` | MIT              |
| [mypy](https://pypi.org/project/mypy/2.4.1/)             |         `>=1.10` |          `2.4.1` | MIT              |

### Build-system requirements

`setuptools>=69` and `wheel` are declared as PEP 517 build-system requirements. They are resolved
in an isolated build environment and are not part of the installed application.

### Python transitive dependencies and IFC-specific notes

Python transitive versions are not locked. The dependency graph includes
`bcf-client`, `odfpy`, `python-dateutil`, `numpy` and other packages pulled in by IfcTester and
other direct dependencies. Do not treat this local resolution as the complete or fixed inventory
for every supported installation.

| Component or asset          | Relationship                                                                                                                                                             | Licence/source status                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `bcf-client` `0.9.0`        | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **To be confirmed.** Its [PyPI 0.9.0 record](https://pypi.org/project/bcf-client/0.9.0/) has a GPLv3 classifier, while the [IfcOpenShell 0.9.0.post1 project description](https://pypi.org/project/ifcopenshell/0.9.0.post1/) lists the BCF library as LGPL-3.0-or-later. The PyPI record has no SPDX expression or licence file metadata. Resolve this upstream discrepancy before redistributing an installed environment. |
| `odfpy` `1.4.1`             | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **To be confirmed.** Its installed metadata lists Apache, GPL and LGPL licence names without an SPDX expression or a clear selection. Verify the package's licence files and applicable grant before redistribution.                                                                                                                                                                                                                                  |
| `python-dateutil` `4.0.0`   | Transitive runtime dependency of IfcTester.                                                                                                                                                    | **To be confirmed.** Installed metadata says `Dual License`; the exact licence choice has not been established.                                                                                                                                                                                                                                                                                                                              |
| IDS 1.0 XSD (`ids.xsd`)     | IfcTester loads this schema from its installed package; first-party code references it but does not copy it into the repository. The schema declares version `1.0.0`.                          | The [buildingSMART IDS repository licence](https://github.com/buildingSMART/IDS/blob/development/LICENSE) identifies CC BY-ND 4.0 and buildingSMART International Ltd. The exact upstream revision corresponding to IfcTester's bundled copy is not recorded. The project does not modify the schema.                                                                                                                                          |
| IfcOpenShell wheel binaries | The Windows wheel contains native DLLs, including Boost-named files. They are installed as part of the external IfcOpenShell dependency, not committed or copied by this repository. | The IfcOpenShell package declares LGPL-3.0-or-later. The licences and notices for every separately bundled native component in a redistributed wheel have not been reviewed; verify them against the exact platform wheel before repackaging it.                                                                                                                                                                                                       |

The application imports IfcOpenShell and IfcTester. `bcf-client` is installed with IfcTester, but
the application does not use it. `ifcclash` is not a dependency.

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

## Images and example files

### Project images

The project author created all of the images below for BIM Intelligence: the artwork was
AI-generated, the panel image is a screenshot of the application, and the research graphics were
supplied by the author. The author holds the rights to publish them and releases them under the
project's [MIT License](./LICENSE). The home-page reel includes a labelled concept visualisation;
it is not a screenshot of the application.

| Files | Use |
| --- | --- |
| [`assets/BIM-Intelligence Architectural Logo.png`](./assets/BIM-Intelligence%20Architectural%20Logo.png) | Project logo in the README |
| [`assets/bim-intelligence-panel.png`](./assets/bim-intelligence-panel.png) | Screenshot of the application's Project Home in the README |
| The other PNG files in [`assets/`](./assets/) | Source artwork for the README and home page |
| [`frontend/public/favicon.svg`](./frontend/public/favicon.svg) | Browser tab icon |
| [`frontend/public/images/home/bim-intelligence-hero.webp`](./frontend/public/images/home/bim-intelligence-hero.webp) | Project Home banner |
| [`frontend/public/images/home/reel/`](./frontend/public/images/home/reel/) (six images) | Project Home image reel |
| [`docs/assets/research/`](./docs/assets/research/) (two graphics) | Research summary graphics |

The research graphics quote figures published by Autodesk, Springer Nature Link and RICS. The
figures belong to their cited sources and have not been
independently checked.

### Example files

| Files | Source and licence | Required credit |
| --- | --- | --- |
| [`examples/duplex-apartment/`](./examples/duplex-apartment/): two spreadsheets and four drawings | Duplex Apartment test files, published by buildingSMART International under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | BSI (2020) "Duplex Apartment Test Files," buildingSMART International. |
| [`examples/molio/Molio_Example.ids`](./examples/molio/Molio_Example.ids) | IDS example whose header records buildingSMART as the copyright holder. The buildingSMART [IDS repository](https://github.com/buildingSMART/IDS) is licensed [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/). | © buildingSMART International Ltd. |
| The `benchmark.ids` files in [`examples/`](./examples/) | Draft IDS files written for this project; [MIT License](./LICENSE) | None |
| [`tests/fixtures/minimal.ifc`](./tests/fixtures/minimal.ifc) and [`minimal.ids`](./tests/fixtures/minimal.ids) | Synthetic fixtures generated by [`make_minimal_ifc.py`](./tests/fixtures/make_minimal_ifc.py); [MIT License](./LICENSE). They reference one Uniclass 2015 code but do not include the classification. | None |

The Duplex Apartment licence asks for the source repository URL in the credit. The files were
originally hosted by the US National Institute of Building Sciences and later republished by
buildingSMART; the current repository URL is still to be added.

The Medical-Dental Clinic collection in [`examples/medical-dental-clinic/`](./examples/medical-dental-clinic/)
contains only a description and a project-authored draft IDS. Its source models are credited as
BSI (2020) "Medical-Dental Test Files," buildingSMART International (CC BY 4.0) and are not
included in the repository.

### Generated build files

| Files | Notes |
| --- | --- |
| `web-ifc.wasm` and `web-ifc-mt.wasm` | Not tracked. [`copy-wasm-assets.mjs`](./frontend/scripts/copy-wasm-assets.mjs) copies them from the locked `web-ifc` `0.0.77` package (MPL-2.0) into the ignored `frontend/public/web-ifc/` directory, and a frontend build includes them. A distributed build must include the MPL-2.0 licence text or a link to it and meet [MPL-2.0 sections 3.1–3.2](https://www.mozilla.org/en-US/MPL/2.0/). |
| IfcOpenShell native wheel contents | Installed as part of the IfcOpenShell package (LGPL-3.0-or-later); not tracked or copied by this repository. |

No third-party JavaScript, WebAssembly, font or native binary files are tracked in the
repository, and the frontend loads no external fonts or hosted assets.

The IDS schema is a separate attribution consideration: the upstream buildingSMART IDS repository
identifies buildingSMART International Ltd. and CC BY-ND 4.0. If the schema is ever copied or
redistributed independently, preserve the required attribution and licence reference, do not
distribute an adapted version under that grant, and first verify the exact provenance of the copy.

## Before redistributing a build

- The Python project has no lockfile. Re-check licences and notices against the exact dependency
  resolution and platform of any distributed build.
- Resolve the `bcf-client` licence discrepancy and the `odfpy` and `python-dateutil` licence
  choices before redistributing an installed Python environment.
- The npm lockfile records a licence field for every package; compare the packages' own
  `LICENSE` and `NOTICE` files for a specific redistribution.
- Full third-party licence texts are not reproduced here. Include the upstream licence texts or
  notices that each distribution form requires.

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
