BeELISA
=======
.. raw:: html

   <div align="center">
       <img src="src/beelisa/resources/icons/beelisa.png" width="220"><br><br>
       <img src="https://img.shields.io/github/v/release/AlAtiat/beelisa">
       <img src="https://img.shields.io/github/license/AlAtiat/beelisa">
       <img src="https://img.shields.io/badge/python-3.11+-blue">
   </div>

 Author: Aun Al Atiat | License: GNU GPLv3

BeELISA is a cross-platform desktop application for the standardized and
reproducible analysis of enzyme-linked immunosorbent assay (ELISA) data in
biomedical research.


Goal of the project
----------------

This software was developed as part of the Bachelor thesis:

    *Statistical Evaluation of Glycoprotein Biomarkers in Pancreatic Ductal
    Adenocarcinoma Using an Analysis Application for ELISA Data Processing
    and Biomarker Pattern Recognition*

    Aun Al Atiat
    Brandenburg University of Technology Cottbus-Senftenberg
    Faculty 2 (Environment and Natural Sciences), Institute of Biotechnology. 2026


Overview
--------

BeELISA provides a structured workflow for quantifying protein biomarkers
from 96-well plate ELISA experiments. It covers the complete analytical
pipeline: raw optical density (OD) import, standard curve fitting,
concentration back-calculation, quality control assessment, and correlation
with clinical metadata.

The application was developed with reproducibility as a primary objective.
All analytical parameters — including curve model selection, clinical metadata parsers (e.g., TNM, UICC), and detection threshold definitions — are dataset-specific yet designed to remain reusable across different datasets.
Clinical metadata parsers are applied only when the corresponding columns (e.g., “TNM” or “UICC”) are present in the dataset.

Scientific Methodology
----------------------

**Standard Curve Fitting**

Calibrant OD measurements are fitted to the following models:

- Linear regression
- Log-linear regression
- Exponential regression
- Four-parameter logistic (4PL)
- Five-parameter logistic (5PL)

Model selection is performed automatically using the Bayesian Information
Criterion (BIC), which penalizes model complexity.
The model with the lowest BIC is applied to back-calculate unknown
concentrations via the inverse curve function.

**Limits of Detection and Quantification**

The limit of detection (LOD) and limit of quantification (LOQ) are
calculated from blank or negative control replicates:

- LOD = mean(blank) + 3 * SD(blank)
- LOQ = mean(blank) + 10 * SD(blank)

When per-plate blank replicates are insufficient, a global estimate
pooled across all plates is used as a fallback.

**Quality Control**

Replicate agreement is assessed by the coefficient of variation (CV):

- Calibrant replicates: warning threshold > 15%
- Sample and control replicates: warning threshold > 20%

**Clinical Correlation**

Quantified biomarker concentrations are correlated with ordinal clinical
staging variables (TNM classification, UICC stage) using Spearman rank
correlation. Multiple testing correction is applied using the
Benjamini-Hochberg false discovery rate (FDR) procedure. Pattern
visualization uses locally weighted scatterplot smoothing (LOWESS).
Batch effects across plates are assessed by principal component analysis
(PCA) of plate-level QC metrics.


Features
--------

- Import of raw plate reader data (CSV, Excel) for standard 96-well plates
- Configurable well classification: calibrant, sample, blank,
  negative control, positive control
- Automatic standard curve model selection via BIC
- Per-plate and global LOD/LOQ calculation
- CV-based replicate QC with configurable thresholds
- Dilution factor correction
- Result classification: below detection, borderline, quantifiable
- TNM/UICC clinical staging integration
- Spearman correlation with Benjamini-Hochberg FDR correction
- Plate-level PCA for batch effect visualization
- Session save and restore (.beelisa format)
- Cross-platform: Windows, macOS, Linux


Installation
------------

BeELISA is distributed as a self-contained native application built using BeeWare Briefcase, bundling the Python runtime and all dependencies.

**Install (Windows)**

Download the latest installer from:

https://github.com/AlAtiat/beelisa/releases

Run the installer.


**Install (macOS)**

Download the appropriate macOS build (Apple Silicon ARM64 or Intel x86_64) from:

https://github.com/AlAtiat/beelisa/releases

Open the downloaded file and move BeELISA to the Applications folder.

If macOS displays a security warning, right-click the application, select “Open”, and confirm.


**Install (Linux – Flatpak)**

Download the latest `.flatpak` package from:

https://github.com/AlAtiat/beelisa/releases

Install via terminal:

    flatpak install BeELISA-1.0.3-x86_64.flatpak

After installation, launch BeELISA from your application menu or run:

    flatpak run org.beelisa.beelisa


Framework and Build System
--------------------------

BeELISA is implemented in Python and built as a native desktop application
using the BeeWare ecosystem.

The graphical user interface (GUI) is developed with:

- BeeWare Toga — a native, cross-platform GUI toolkit for Python.

Application packaging and distribution are handled using:

- BeeWare Briefcase — a tool for building standalone installers for
  Windows, macOS, and Linux.

The BeeWare project enables Python applications to run as fully native
desktop software without requiring users to install Python separately.

For more information, see:

- BeeWare: https://beeware.org
- Toga: https://beeware.org/project/projects/libraries/toga/
- Briefcase: https://beeware.org/project/projects/tools/briefcase/

**Development Dependencies**

Python 3.11+

Core libraries:
    pandas>=2.2,<2.4
    numpy>=1.26,<2.0
    scipy==1.13.1
    scikit-learn>=1.4,<1.6
    matplotlib>=3.8,<3.11
    seaborn==0.13.2
    openpyxl>=3.1,<4.0
    toga

License
-------

Copyright (C) 2026 Aun Al Atiat.

This software is distributed under the terms of the
GNU General Public License v3.0 (GPLv3) or any later version.
See the ``LICENSE`` file for the full license text.


Citation
--------

If you use BeELISA in research, please cite the associated thesis:

    Al Atiat, A. (2026). *Statistical Evaluation of Glycoprotein Biomarkers
    in Pancreatic Ductal Adenocarcinoma Using an Analysis Application for
    ELISA Data Processing and Biomarker Pattern Recognition*. Bachelor
    thesis, Brandenburg University of Technology Cottbus-Senftenberg.
