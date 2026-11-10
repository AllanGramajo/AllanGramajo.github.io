# Heart and Chest Radar — public recording laboratory

**Allan Gramajo and Alan Acosta — equal project contributors.**

## [Open the interactive radar website](https://allangramajo.github.io/Heart-and-Chest-radar/)

Open the website, choose **Recordings**, select one of **eight public MobiVital CSV recordings**, and press **Play recording**. Visitors do not need a GitHub account, publication settings, a download, or a CSV import.

This directory publishes the restored eight-recording version at the original project address. The organization repository currently has a separate older, single-recording deployment. This release uses the existing personal Pages site because the connection can write here; it does not modify organization permissions or replace the portfolio homepage.

## Actual recorded samples

All eight original CSV files are included in the HTML, losslessly gzip-compressed. The page checks each file's SHA-256 before parsing it. Switching recordings makes no data request. Playback shows measured samples over time, not live sensor acquisition. The breathing-rate estimates, normalized radar/belt waveforms, and other diagnostics use the existing full-window offline teaching baseline; this is not the published learned MobiVital model or a validated clinical device.

Controls include recording selection, play/pause, restart, time seeking, 0.5x–4x playback, manual or radar-only automatic range-bin selection, analysis export, and **Save complete offline website**. Saved HTML retains all eight recordings and the current selection. The four original physics simulations remain separate and explicitly simulated.

## Source and attribution

Original source: [UCLA NESL MobiVital dataset](https://github.com/nesl/MobiVital-dataset), pinned revision `42572b4231be0d43a9be0690c30c48ca4427a65c`.

Dataset DOI: [10.5281/zenodo.15022885](https://doi.org/10.5281/zenodo.15022885). Reuse: Creative Commons Attribution 4.0 International, verified from dataset metadata. Author attribution, individual source URLs, Git object IDs, SHA-256 checksums, and license evidence are retained in [the data manifest](data/manifest.json), [license evidence](data/license-evidence.json), and [attribution](ATTRIBUTION.md).

Each selected segment contains 1,500 rows × 254 columns, with 50 Hz sampling and approximately 30 seconds of recording. These selected public segments are not population-level or clinical validation. The radar/belt recording is distinct from the 62 GHz simulations and the simulated chest map is not a measured lung-function image.

## Maintainers

The original website source is pinned to organization-repository commit `d83732f4ea7c3bde514b6e7becfcc1d00a98e68e`. The additive restoration scripts are in [`_radar_build`](../_radar_build/). They assemble the original website, preserve the research and physics sections, verify the dataset, restore selection/playback, and test it before publishing the generated file here.

The **Build restored radar recording library** workflow builds and tests on the restoration branch, then commits only generated radar files on that branch. Review and merge the branch to `main` to publish through the existing Pages configuration. The portfolio's root `index.html`, resume and other content are not replaced.

The **Verify radar website links** workflow checks the public deployment anonymously and tests its recording controls in Chromium. These checks demonstrate software behavior and sample identity, not physiological accuracy.
