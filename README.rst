BeELISA
=======
.. raw:: html

   <div align="center">
       <img src="src/beelisa/resources/icons/beelisa.png" width="220"><br><br>
       <img src="https://img.shields.io/github/v/release/AlAtiat/beelisa">
       <img src="https://img.shields.io/github/license/AlAtiat/beelisa">
       <img src="https://img.shields.io/badge/python-3.11+-blue">
   </div>

 Author: Aun Al Atiat

BeELISA is a cross-platform desktop application for the standardized and
reproducible analysis of enzyme-linked immunosorbent assay (ELISA) data in
biomedical research.


Goal of the project
----------------

This software was developed as part of the Bachelor thesis:

    *Statistical Evaluation of Glycoprotein Biomarkers in Cancer Using an Analytical Application for ELISA Data Processing and Biomarker Pattern Recognition* (not public)

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


All you need
------------

BeELISA requires at least three input tables/files: one plate OD file, the corresponding plate ID file, and one metadata file. The plate OD and plate ID files should follow the same 96-well plate layout and can be provided as `.csv` or `.xlsx` files. The plate ID file defines which sample is located in each well, while the plate OD file contains the corresponding optical density measurement for each well. The metadata file is a normal table with a header row and columns describing the samples; it must contain a sample ID column that matches the IDs used in the plate ID file. The plate design itself is configured inside the software.

.. raw:: html

   <table align="center" width="100%">
   <tr>

   <td width="33%" valign="top" align="center">
   <details>
   <summary><b>Plate ID file</b></summary>
   <br>
   <table border="1" cellpadding="3" cellspacing="0" style="font-size:11px; text-align:center;">
   <tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>7</th><th>8</th><th>9</th><th>10</th><th>11</th><th>12</th></tr>
   <tr><th>A</th><td>STD1</td><td>STD1</td><td>S001</td><td>S002</td><td>S003</td><td>S004</td><td>S005</td><td>S006</td><td>S007</td><td>S008</td><td>S009</td><td>S010</td></tr>
   <tr><th>B</th><td>STD2</td><td>STD2</td><td>S011</td><td>S012</td><td>S013</td><td>S014</td><td>S015</td><td>S016</td><td>S017</td><td>S018</td><td>S019</td><td>S020</td></tr>
   <tr><th>C</th><td>STD3</td><td>STD3</td><td>S021</td><td>S022</td><td>S023</td><td>S024</td><td>S025</td><td>S026</td><td>S027</td><td>S028</td><td>S029</td><td>S030</td></tr>
   <tr><th>D</th><td>STD4</td><td>STD4</td><td>S031</td><td>S032</td><td>S033</td><td>S034</td><td>S035</td><td>S036</td><td>S037</td><td>S038</td><td>S039</td><td>S040</td></tr>
   <tr><th>E</th><td>STD5</td><td>STD5</td><td>S041</td><td>S042</td><td>S043</td><td>S044</td><td>S045</td><td>S046</td><td>S047</td><td>S048</td><td>S049</td><td>S050</td></tr>
   <tr><th>F</th><td>NEG</td><td>NEG</td><td>S051</td><td>S052</td><td>S053</td><td>S054</td><td>S055</td><td>S056</td><td>S057</td><td>S058</td><td>S059</td><td>S060</td></tr>
   <tr><th>G</th><td>S061</td><td>S062</td><td>S063</td><td>S064</td><td>S065</td><td>S066</td><td>S067</td><td>S068</td><td>S069</td><td>S070</td><td>S071</td><td>S072</td></tr>
   <tr><th>H</th><td>S073</td><td>S074</td><td>S075</td><td>S076</td><td>S077</td><td>S078</td><td>S079</td><td>S080</td><td>S081</td><td>S082</td><td>S083</td><td>S084</td></tr>
   </table>
   <p>The ID file contains the sample or calibrator identifier assigned to each well.</p>
   <p><code>resources/synthetic_data_1/plates/PLATE_001_ID.xlsx</code></p>
   </details>
   </td>

   <td width="33%" valign="top" align="center">
   <details>
   <summary><b>Plate OD file</b></summary>
   <br>
   <table border="1" cellpadding="3" cellspacing="0" style="font-size:11px; text-align:center;">
   <tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>7</th><th>8</th><th>9</th><th>10</th><th>11</th><th>12</th></tr>
   <tr><th>A</th><td>2.102</td><td>2.087</td><td>0.812</td><td>0.743</td><td>1.031</td><td>0.655</td><td>0.912</td><td>1.223</td><td>0.534</td><td>0.689</td><td>0.771</td><td>0.845</td></tr>
   <tr><th>B</th><td>1.742</td><td>1.735</td><td>0.621</td><td>0.583</td><td>0.711</td><td>0.902</td><td>0.488</td><td>0.557</td><td>0.632</td><td>0.784</td><td>0.846</td><td>0.923</td></tr>
   <tr><th>C</th><td>1.203</td><td>1.190</td><td>0.445</td><td>0.512</td><td>0.601</td><td>0.734</td><td>0.821</td><td>0.944</td><td>0.377</td><td>0.425</td><td>0.503</td><td>0.588</td></tr>
   <tr><th>D</th><td>0.742</td><td>0.755</td><td>0.389</td><td>0.467</td><td>0.529</td><td>0.612</td><td>0.703</td><td>0.812</td><td>0.356</td><td>0.441</td><td>0.532</td><td>0.608</td></tr>
   <tr><th>E</th><td>0.332</td><td>0.341</td><td>0.288</td><td>0.355</td><td>0.402</td><td>0.481</td><td>0.552</td><td>0.624</td><td>0.298</td><td>0.344</td><td>0.421</td><td>0.509</td></tr>
   <tr><th>F</th><td>0.091</td><td>0.087</td><td>0.251</td><td>0.316</td><td>0.389</td><td>0.456</td><td>0.518</td><td>0.587</td><td>0.246</td><td>0.309</td><td>0.376</td><td>0.462</td></tr>
   <tr><th>G</th><td>0.271</td><td>0.335</td><td>0.412</td><td>0.506</td><td>0.577</td><td>0.643</td><td>0.725</td><td>0.809</td><td>0.286</td><td>0.359</td><td>0.421</td><td>0.498</td></tr>
   <tr><th>H</th><td>0.312</td><td>0.384</td><td>0.456</td><td>0.529</td><td>0.604</td><td>0.681</td><td>0.759</td><td>0.833</td><td>0.337</td><td>0.408</td><td>0.492</td><td>0.561</td></tr>
   </table>
   <p>The OD file contains the optical density reading for each well in the same layout.</p>
   <p><code>resources/synthetic_data_1/plates/PLATE_001_OD.xlsx</code></p>
   </details>
   </td>

   <td width="33%" valign="top" align="center">
   <details>
   <summary><b>Metadata file</b></summary>
   <br>
   <table border="1" cellpadding="4" cellspacing="0" style="font-size:12px; text-align:center;">
   <tr><th>sample_id</th><th>group</th><th>age</th><th>sex</th><th>stage</th></tr>
   <tr><td>S001</td><td>PDAC</td><td>61</td><td>F</td><td>II</td></tr>
   <tr><td>S002</td><td>PDAC</td><td>57</td><td>M</td><td>III</td></tr>
   <tr><td>S003</td><td>Control</td><td>45</td><td>F</td><td>NA</td></tr>
   <tr><td>S004</td><td>PDAC</td><td>69</td><td>M</td><td>IV</td></tr>
   <tr><td>S005</td><td>Control</td><td>52</td><td>F</td><td>NA</td></tr>
   </table>
   <p>The metadata file contains additional information for each sample. The sample ID column must match the IDs in the plate ID file.</p>
   <p><code>resources/synthetic_data_1/metadata.xlsx</code></p>
   </details>
   </td>

   </tr>
   </table>



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

.. raw:: html

   <table align="center"><tr>
   <td align="center"><a href="resources/images/RESULTS_Plot_Curve.png"><img src="resources/images/RESULTS_Plot_Curve.png" width="200" alt="Standard curve fit"/></a></td>
   <td align="center"><a href="resources/images/RESULTS_MODEL_COMP.png"><img src="resources/images/RESULTS_MODEL_COMP.png" width="200" alt="Model comparison"/></a></td>
   </tr></table>

**Limits of Detection and Quantification**

The limit of detection (LOD) and limit of quantification (LOQ) are
calculated from blank or negative control replicates:

- LOD = mean(blank) + 3 * SD(blank)
- LOQ = mean(blank) + 10 * SD(blank)

When per-plate blank replicates are insufficient, a global estimate
pooled across all plates is used as a fallback.

**Inter-Plate Factor Correction**

When multiple plates are analyzed together, systematic differences in signal
intensity between plates (e.g., due to different reagent lots, incubation
conditions, or plate reader variation) can bias concentration estimates.
BeELISA implements a multiplicative inter-plate factor correction based on
calibrant wells, analogous to the ΔΔCt normalisation used in qPCR. (Ruijter et al., 2015 — Between-run correction for multi-plate qPCR experiments.
Biomolecular Detection and Quantification.) (https://doi.org/10.1016/j.bdq.2015.07.001)

For each calibrant dilution level *k*, the across-plate median OD of all
plates is used as a reference *r_k*. A plate-specific correction factor is
then computed as:

    F_plate = exp( median_k( log( m_{p,k} / r_k ) ) )

where *m_{p,k}* is the median OD of calibrant replicates for plate *p* at
level *k*, and the outer median is taken over all valid calibrant levels
(those with *r_k > 0*). Corrected ODs are obtained by dividing all wells on
the plate by *F_plate*. LOD and LOQ thresholds are scaled by the same factor.

If plates are assigned to groups, correction factors are computed independently
within each group so that between-group biological differences are preserved.

**Quality Control**

Replicate agreement is assessed by the coefficient of variation (CV):

- Calibrant replicates: warning threshold > 15%
- Sample and control replicates: warning threshold > 20%

.. raw:: html

   <table align="center"><tr>
   <td align="center"><a href="resources/images/heatmap_PLATE_007_OD.xlsx.png"><img src="resources/images/heatmap_PLATE_007_OD.xlsx.png" width="200" alt="OD heatmap"/></a></td>
   <td align="center"><a href="resources/images/RESULTS_QC.png"><img src="resources/images/RESULTS_QC.png" width="200" alt="QC report"/></a></td>
    <td align="center"><a href="resources/images/pca_analysis.png"><img src="resources/images/pca_analysis.png" width="200" alt="PCA batch analysis"/></a></td>
   </tr></table>

**Clinical Correlation**

Quantified biomarker concentrations are correlated with ordinal clinical
staging variables (TNM classification, UICC stage) using Spearman rank
correlation. Multiple testing correction is applied using the
Benjamini-Hochberg false discovery rate (FDR) procedure. Pattern
visualization uses locally weighted scatterplot smoothing (LOWESS).
Batch effects across plates are assessed by principal component analysis
(PCA) of plate-level QC metrics.

.. raw:: html

   <table align="center"><tr>
   <td align="center"><a href="resources/images/trend_3_grid.png"><img src="resources/images/trend_3_grid.png" width="200" alt="LOWESS pattern grid"/></a></td>
   <td align="center"><a href="resources/images/correlation_heatmap_2_GP2_IgA.png"><img src="resources/images/correlation_heatmap_2_GP2_IgA.png" width="200" alt="Correlation heatmap"/></a></td>
   </tr></table>

**ROC / Diagnostic Performance Analysis**

When a binary clinical outcome is available (e.g. disease vs control),
BeELISA evaluates the diagnostic performance of the biomarker using
Receiver Operating Characteristic (ROC) analysis.

The ROC curve is generated by varying the decision threshold of the
selected score variable (e.g. concentration or OD value) and calculating
the corresponding sensitivity (true positive rate) and false positive
rate (1 − specificity).

Overall classification performance is summarized by the area under the
ROC curve (AUC):

- AUC = 0.5 indicates random classification
- AUC = 1.0 indicates perfect discrimination

The optimal cutoff value is determined using the **Youden index**
(sensitivity + specificity − 1), which identifies the threshold that
maximizes the combined sensitivity and specificity.

The ROC plot reports:

- AUC with 95% confidence interval
- Optimal cutoff value
- Sensitivity and specificity at the cutoff
- Sample sizes of the positive and negative groups

Uncertainty of the ROC curve is estimated using bootstrap resampling to
generate a 95% confidence band.

.. raw:: html

   <p align="center"><a href="resources/images/roc_1_GP2_ISO1_IgA.png"><img src="resources/images/roc_1_GP2_ISO1_IgA.png" width="200" alt="ROC curve"/></a></p>

Features
--------

- Import of raw plate reader data (CSV, Excel) for standard 96-well plates
- Configurable well classification: calibrant, sample, blank,
  negative control, positive control
- Automatic standard curve model selection via BIC
- Per-plate and global LOD/LOQ calculation
- CV-based replicate QC with configurable thresholds
- Dilution factor correction
- per group Multiplicative inter-plate factor correction of standard curves
- Result classification: below detection, borderline, quantifiable
- TNM/UICC clinical staging integration
- Spearman correlation with Benjamini-Hochberg FDR correction
- Plate-level PCA for batch effect visualization
- ROC-based diagnostic performance analysis with AUC estimation, optimal cutoff determination (Youden index), and sensitivity/specificity reporting
- Session save and restore (.beelisa format)
- Cross-platform: Windows, macOS, Linux

.. raw:: html

   <table align="center"><tr>
   <td align="center"><a href="resources/images/ELISAVIEW.png"><img src="resources/images/ELISAVIEW.png" width="200" alt="ELISA import view"/></a></td>
   <td align="center"><a href="resources/images/DATAVIEW.png"><img src="resources/images/DATAVIEW.png" width="200" alt="Data view"/></a></td>
   </tr><tr>
   <td align="center"><a href="resources/images/ANALYSISVIEW.png"><img src="resources/images/ANALYSISVIEW.png" width="200" alt="Analysis configuration"/></a></td>
   <td align="center"><a href="resources/images/RESULTS_TABLE.png"><img src="resources/images/RESULTS_TABLE.png" width="200" alt="Results table"/></a></td>
   </tr></table>


Download
--------

.. raw:: html

   <table align="center">
   <tr>
   <td align="center" width="25%">
     <h3>Windows</h3>
     <a href="https://github.com/AlAtiat/beelisa/releases/latest/download/BeELISA.msi">
       <img src="https://img.shields.io/badge/Download%20Installer-.msi-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Download for Windows"/>
     </a>
     <br><br>
     <sub>Windows 10 / 11 · MSI Installer<br>Run the installer</sub>
   </td>
   <td align="center" width="25%">
     <h3>macOS</h3>
     <a href="https://github.com/AlAtiat/beelisa/releases/latest/download/BeELISA-arm64.dmg">
       <img src="https://img.shields.io/badge/Apple_Silicon_(M1%2FM2%2FM3)-DMG-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Download for macOS ARM64"/>
     </a>
     <br>
     <a href="https://github.com/AlAtiat/beelisa/releases/latest/download/BeELISA-x86_64.dmg">
       <img src="https://img.shields.io/badge/Intel_(x86__64)-DMG-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Download for macOS Intel"/>
     </a>
     <br><br>
     <sub>macOS 12+ · DMG · Open the DMG and drag BeELISA to Applications.</sub>
   </td>
    <td align="center" width="25%">
     <h3>Linux (AppImage)</h3>
     <a href="https://github.com/AlAtiat/beelisa/releases/latest/download/BeELISA.AppImage">
       <img src="https://img.shields.io/badge/Download%20AppImage-.AppImage-4CAF50?style=for-the-badge&logo=linux&logoColor=white" alt="Download AppImage for Linux"/>
     </a>
     <br><br>
     <sub>All distributions · No install needed:<br><code>chmod +x BeELISA.AppImage &amp;&amp; ./BeELISA.AppImage</code></sub>
   </td>
   <td align="center" width="25%">
     <h3>Linux (Flatpak)</h3>
     <a href="https://github.com/AlAtiat/beelisa/releases/latest/download/BeELISA.flatpak">
       <img src="https://img.shields.io/badge/Download%20Flatpak-.flatpak-E95420?style=for-the-badge&logo=linux&logoColor=white" alt="Download for Linux"/>
     </a>
     <br><br>
     <sub>All distributions · Install via:<br><code>flatpak install BeELISA.flatpak</code></sub>
   </td>
   </tr>
   </table>

   <p align="center"><sub>
   Links above always point to the latest release.
   All releases and release notes are on the
   <a href="https://github.com/AlAtiat/beelisa/releases">Releases page</a>.
   </sub></p>


.. Installation
.. ------------

.. BeELISA is distributed as a self-contained native application built using BeeWare Briefcase, bundling the Python runtime and all dependencies.

.. **Install (Windows)**

.. Download the latest installer from:

.. https://github.com/AlAtiat/beelisa/releases

.. Run the installer.


.. **Install (macOS)**

.. Download the appropriate macOS build (Apple Silicon ARM64 or Intel x86_64) from:

.. https://github.com/AlAtiat/beelisa/releases

.. Open the downloaded file and move BeELISA to the Applications folder.

.. If macOS displays a security warning, right-click the application, select “Open”, and confirm.


.. **Install (Linux – Flatpak)**

.. Download the latest `.flatpak` package from:

.. https://github.com/AlAtiat/beelisa/releases

.. Install via terminal:

.. Ubuntu / Debian::

..     sudo apt install flatpak

..     sudo flatpak install BeELISA-1.0.4-x86_64.flatpak

.. After installation, launch BeELISA from your application menu or run:

..     flatpak run org.beelisa.beelisa


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

If you use BeELISA in research, please cite as:

    Al Atiat, A. (2026). *BeELISA: A Software Framework for ELISA Data Analysis* (Version 1.0.7) [Computer software]. GitHub. https://github.com/AlAtiat/beelisa
