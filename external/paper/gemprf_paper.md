# GEM-pRF: GPU-empowered mapping of population receptive fields for large-scale fMRI analysis

**Authors:** Siddharth Mittal, Michael Woletz, David Linhardt, Christian Windischberger

**Affiliation:** High Field MR Center, Center for Medical Physics and Biomedical Engineering, Medical University of Vienna, Austria

**Corresponding author:** Christian Windischberger (christian.windischberger@meduniwien.ac.at)

**Citation:** Medical Image Analysis 109 (2026) 103891. https://doi.org/10.1016/j.media.2025.103891

**Keywords:** Retinotopy; Population receptive fields; fMRI; General linear model; GPU-empowered pRF mapping

## Abstract

Population receptive field (pRF) mapping is a fundamental technique for understanding retinotopic organisation of the human visual system. Since its introduction in 2008, however, its scalability has been severely hindered by the computational bottleneck of iterative parameter refinement. Current state-of-the-art implementations either sacrifice precision for speed or rely on slow iterative parameter updates, limiting their applicability to large-scale datasets. Here, we present a novel mathematical reformulation of the General Linear Model (GLM), wrapped in a GPU-Empowered Mapping of population Receptive Fields (GEM-pRF) software implementation. By orthogonalizing the design matrix, our approach enables the direct and fast computation of the objective function's derivatives, which are used to eliminate the iterative refinement process. This approach dramatically accelerates pRF estimation with high accuracy. Validation using empirical and simulated data confirms GEM-pRF's accuracy, and benchmarking against established tools demonstrates a reduction in computation time of almost two orders of magnitude. With its modular and extensible design, GEM-pRF provides a critical advancement for large-scale fMRI retinotopic mapping. Furthermore, our reformulated GLM approach in combination with GPU-based implementation offers a broadly applicable solution that may extend beyond visual neuroscience, accelerating computational modelling across various domains in neuroimaging and beyond.

## 1. Introduction

Within neuroscience, the research domain of retinotopic mapping is dedicated to unravelling the relationship between the visual field and the visual cortex. Since early observations in the 1900s suggested a direct mapping between the visual field and visual cortex (Holmes, 1918; Tatsuji, 1909), many researchers have engaged in the development of techniques for assessing the retinotopic features of the visual system (for a review see Wandell and Winawer, 2011). Notably, functional magnetic resonance imaging (fMRI)-based techniques have become pivotal for non-invasive retinotopic experiments based on travelling waves stimuli (DeYoe et al., 1994; Engel et al., 1994). Numerous studies have established a functional topographic mapping of the human visual system using Positron-Emission Tomography (PET) (Fox et al., 1987; Zeki et al., 1991) and fMRI (Schneider et al., 1993). In particular, Sereno et al. (1995) proposed mapping the retinotopic organisation of multiple visual areas on the cortical surface based on phase information in fMRI data using periodic visual stimulation. Taking into consideration the eccentricities and polar angles of the corresponding receptive fields, they were able to functionally segment visual area regions such as V1, V2, VP, V3, and V4.

At the beginning of the twenty-first century, a new mathematical model for retinotopic analysis was proposed, referred to as population receptive field (pRF) mapping (Dumoulin and Wandell, 2008). Unlike previous methods, this approach is no longer limited to periodic stimulus designs and thus allows the use of arbitrary visual stimuli.

Numerous studies have used the pRF approach for visual field mapping (Benson et al., 2022; Bridge et al., 2023; Elul and Levin, 2024; Groen et al., 2022). In addition, applications in healthy participants with simulated visual field deficits (Haak et al., 2012; Hummer et al., 2018; Linhardt et al., 2022) and in clinical populations have demonstrated the potential of pRF mapping for staging retinal pathologies and tracking retinal disease progression (Molz et al., 2023; Prabhakaran et al., 2021; Ritter et al., 2019, 2024). These studies collectively enhance our understanding of visual field mapping in both simulated and actual vision loss. Another application of retinotopic mapping is the decoding of visual information, which is crucial for developing brain-computer interface (BCI) devices. These devices could one day reliably reconstruct cortical activity to the visual field, from reconstructing perceived or imagined letters (Senden et al., 2019) to complex visual scenes (Takagi and Nishimoto, 2023).

The pRF mapping technique involves computing predicted time courses for each pRF given a set of model parameters. These time courses ultimately depend on the visual stimulus used in the experiment and the chosen pRF model, such as the isotropic 2D Gaussian (Dumoulin and Wandell, 2008) or the difference of Gaussians (Zuiderbaan et al., 2012). The algorithm then identifies the best-fit model signal for the measured fMRI time course in every voxel to estimate the pRF parameters spatial position (μx, μy) and other chosen model's parameters (such as size (σ) in case of 2D isotropic Gaussian model). This fitting procedure uses optimisation algorithms to minimise the difference between the predicted and measured fMRI time courses. It typically involves a two-stage process where initial coarse fitting is followed by refined fitting. Notably, the refined fitting procedure is commonly built as an iterative, computationally demanding optimisation process.

Several implementations of pRF mapping are currently used in the field. The two most often used software packages are mrVista (Dumoulin and Wandell, 2008) and SamSrf (D. Sam Schwarzkopf, 2018), which both follow the gold-standard, straight-forward approach with two fitting steps as described above. These software packages are, however, limited to perform computations on the CPU only and thus require long processing times of many hours or even days, particularly with large data sets. There are other pRF mapping implementations such as DeepRF (Thielen et al., 2019), fast-pRF (Bhat et al., 2021) and qPRF (Waz et al., 2025), which specifically aim to minimise computational times. DeepRF uses a deep learning-based approach that requires model training to predict the pRF parameters for the measured fMRI data. Training the deep learning model for the DeepRF approach takes several hours and each specific experiment setup requires a separate model trained with the same setup. Given the long training time and the necessity for identical experimental setups between test and training data, this pRF mapping implementation might not be optimal for scenarios requiring frequent configuration changes. On the other hand, the fast-pRF method makes the pRF mapping procedure very fast on the CPU, however, it suffers from a loss in fitting precision. Therefore, it is only suitable for applications where accuracy can be sacrificed in favour of faster execution times, as e.g. real-time applications. Lastly, the qPRF method uses a searchable similarity-based tree to refine pRF parameters efficiently. By storing neighbour relationships, it enables rapid refinement. However, tree construction takes several hours, which may be a consideration for studies requiring frequent reconfiguration, such as comparative analyses with varying stimuli. Considering the currently available toolboxes, there is a gap in pRF mapping implementations for applications that require highly accurate estimations combined with minimal computation times.

Computing power saw a boost in the mid-2000s when Graphics Processing Units (GPUs) whose application was initially limited to graphics processing became available for high-performance computing via the introduction of the Compute Unified Device Architecture (CUDA) libraries on General-Purpose GPU (GPGPU) hardware. Interestingly, most commonly used software packages for pRF analysis do not take full advantage of the computational power provided by GPUs. This is partly because the mathematics involved in pRF mapping are not easily transferred to the parallel processing paradigm of GPUs. Typically, fMRI data processing steps utilise a general multivariate regression model, also known as the General Linear Model (GLM) (Poline and Brett, 2012). In the case of pRF mapping, as proposed by Dumoulin and Wandell (2008), the application of GLM is required in both coarse as well as refine-fitting steps. However, during the refine-fitting process, the GLM needs to be applied iteratively to find the pRF parameter estimations. These requirements have made it challenging to implement a GPU-based pRF analysis application as GPUs are best suited for applications involving Single Instruction, Multiple Data (SIMD) processing.

To address these deficits, we have reformulated parts of the fitting problem and have implemented this approach to use Graphics Processing Unit (GPU) acceleration in a novel software package developed from scratch called GPU-Empowered Mapping of pRF or GEM-pRF. GEM-pRF takes full advantage of the computational capabilities of currently available GPUs and optimises the refine fitting procedure by avoiding the requirement of iterative optimisation.

In this study, we propose a novel implementation of pRF analysis based on a modified linear regression method, which can organise the data operations to follow a SIMD pattern. Our approach of GPU-Empowered Mapping of pRF (GEM-pRF) is encapsulated within a Python-based software package using CUDA libraries. To optimise efficiency and enable easy exploration of various setups, our methodology specifically employs the CuPy package—an open-source Python wrapper for CUDA (Okuta et al., 2017). Specifically designed for GPU operations, it follows NumPy's API structure and includes the CUDA C++ runtime library NVRTC (Raschka et al., 2020), providing a Python API for compiling and executing CUDA kernels at runtime. This key feature enables the integration of native CUDA kernels (implemented in C/C++) to accommodate diverse pRF modelling approaches. We demonstrate the accuracy and applicability of GEM-pRF on both simulated and empirical data to show how GEM-pRF enables high-accuracy pRF analyses with greatly reduced processing time.

## 2. Methods

### 2.1. pRF modelling and fitting in GEM-pRF

The general idea behind pRF mapping is to generate expected time courses for the BOLD (blood-oxygen-level-dependent) signal based on a pRF model, a stimulus aperture, and a hemodynamic response function (HRF). The stimulus data depends on the experimental paradigm and must be provided as input for the analysis. As the HRF reflects a neurophysiological phenomenon, it varies between subjects. While some software implementations allow the computation of a subject-specific HRF, our software is designed to use either user-defined HRF values or a standard HRF as input. Consequently, while the stimulus and the HRF are typically assumed constant across voxels for a given experiment and subject, the pRF model depends on several parameters that must be estimated on a voxel-by-voxel basis. Following a similar methodology to the pRF fitting procedure outlined by Dumoulin and Wandell (2008), our implementation adopts a coarse-to-fine fitting strategy to estimate the pRF parameters for each measured fMRI time course. However, our approach introduces a novel streamlined linear regression method, optimised for high performance through GPU acceleration and a novel one-step fine-fitting procedure without the need for iterative procedures.

In classic pRF modelling, a pRF is represented as a function of spatial position in the visual field, denoted by μx and μy, which corresponds to the centre coordinates of the receptive field. Additional parameters, such as the receptive field size σ, may also be included depending on the chosen pRF model. For instance, a commonly used model is based on a 2D Gaussian function, where σ defines the isotropic standard deviation of the Gaussian receptive field.

Mathematically, a pRF can be expressed as a function fij(θ) that depends on a set of K parameters, where θ ∈ R^K, while the indices i and j represent the spatial positions in the visual field. In this paper, we focus on the 2D Gaussian pRF model with K = 3 parameters, which leads to θ = (μx, μy, σ). However, more complex models incorporating additional parameters can also be implemented in the GEM-pRF framework.

Another essential aspect in computing predicted time courses is the stimulus aperture, which determines the neuronal response patterns elicited during a pRF mapping experiment. The stimulus aperture can be mathematically defined as a three-dimensional matrix S ∈ [0, 1]^(U×V×T), where U × V represents the spatial dimensions of the stimulus grid, T is the number of time points in the experiment, and each element of S takes a value between either 0 (no stimulus) or 1 (stimulus present).

When a visual stimulus appears at a particular location and time, it triggers neural responses. These responses are typically modelled using the HRF, denoted as h(t), which describes the linear response of the BOLD signal to a neural event. Given this, a pRF model time course p(θ) corresponding to a particular parameter combination θ can be computed as:

p(θ) = h(t) * (Σ_i^U Σ_j^V S_ij(t) f_ij(θ))

Considering the linearity of convolution, we can first convolve the given stimulus S with h(t) and then use the HRF-convolved stimulus Ŝ version to compute the model time courses:

Ŝ_ij(t) = h(t) * S_ij(t)
p(θ) = Σ_i^U Σ_j^V Ŝ_ij f_ij(θ)      (Eq. 1)

For pRF mapping analysis, the general linear model (Friston et al., 1995) is used. This model uses linear least squares optimisation with a design matrix including effects of interest and additional confounds to model the task-based BOLD effect. The design matrix X, with a model time course p(θ) for a particular modelling parameter combination θ, and the additional regressor matrix R can therefore be represented as:

X = [p(θ) R]      (Eq. 2)

The regressor matrix R may contain different nuisance regressors and low-frequency functions, but, for the purpose of this work, must at least contain a constant term. Based on ordinary least squares fitting, the residuals ê between a measured time course y and a prediction ŷ can be represented as:

ê = [I − X(X^T X)^(−1) X^T] y      (Eq. 3)

where I represents an identity matrix.

Since the prediction is invariant with respect to a change of basis in the column space of the design matrix, we can replace the design matrix with an orthonormal version. We assume the regressor matrix R to be already orthogonalized (e.g. by using Gram-Schmidt or QR decomposition) and then explicitly orthogonalizing each pRF model time course p(θ) with respect to R. The result is then normalised and denoted as p'(θ), which represents a prediction time course. This results in an orthonormalized regressor matrix X':

X' = [p'(θ) R]      (Eq. 4)

Upon substituting the modified regressor matrix X' in Eq. 3 for residual errors, and solving it for the residual sum of squares (RSS):

ê^T ê = y^T y − y^T p'(θ) p'(θ)^T y − y^T R R^T y
       = y^T y − (y^T p'(θ))^2 − y^T R R^T y      (Eq. 5)

In pRF mapping, the ultimate goal is to compute θ that minimises RSS. Both y^T y and y^T R R^T y are independent of θ, so RSS depends on the prediction time course solely through the term (y^T p'(θ))^2. Maximising this term corresponds to finding the prediction time course that minimises the residual error. Since the goal is to find a prediction time course that correlates highly with the fMRI time course y (strong positive correlation), we can safely drop the square and define the objective function:

C(θ) = y^T p'(θ)      (Eq. 6)

The coarse fitting step tries to maximize C(θ):

θ̂ = argmax_θ C(θ)      (Eq. 7)

#### 2.1.1. Coarse fitting

Given a set Θ of N parameter combinations θ, the best fitting coarse parameter combination θ̂_c for a measured time course y in the coarse fitting step is:

θ̂_c = argmax_θ C(θ), θ ∈ Θ      (Eq. 8)

This can be efficiently implemented on a GPU, or in other parallelised systems, by constructing matrices from the prediction and measured time courses and performing a matrix multiplication, followed by an argmax operation. In GEM-pRF, this is implemented on the GPU using custom CUDA kernels in C/C++ alongside Python's CuPy library.

Our proposed method of using an orthogonalized design matrix eliminates the need for computing beta weights explicitly. This effectively reduces the computational load and enables the explicit computation of derivatives of the RSS objective function which is used for improving the initial coarse-fitting solution.

#### 2.1.2. Refine fitting

After the initial coarse fitting, where the optimal pRF parameters are selected from a discrete sampling space Θ, a fine-fitting step is performed to refine these estimates. Given a sufficiently dense sampling space Θ and a smooth objective function C(θ), the global maximum is expected to be in the vicinity of the coarse-fit solution. In our implementation, the refinement step efficiently determines this maximum without requiring iterative optimisation.

##### 2.1.2.1. Quadratic approximation for refinement

Traditional pRF mapping methods are based on iterative refinement of coarse estimates for each measured fMRI signal y, which is computationally expensive. Instead, GEM-pRF takes advantage of prediction time courses and their derivatives available on GPU side to compute the derivatives of the objective function directly, thus reducing overall computation times. This enables a non-iterative refinement based on a quadratic approximation of the residual sum of squares (RSS) values in the local neighbourhood of the coarse-fit parameters.

Denoting the estimated coarse-fit parameters as θ̂_c, we consider the objective function values in their local neighbourhood Θ_N ⊆ Θ. These values are approximated using a multidimensional quadratic function:

C(θ) ≈ ε(θ) = θ^T A θ + b^T θ + c      (Eq. 9)

where A is a symmetric square matrix, b is a vector, and c is a scalar. A, b and c are estimated using a linear least-squares fit to the function values C(θ) and their partial derivatives in the neighbourhood of θ̂_c for each parameter combination θ using:

∂C(θ)/∂θ_k = y^T ∂p'(θ)/∂θ_k      (Eq. 10)

The first-order derivative of ε with respect to θ is:

∇ε(θ) = 2Aθ + b      (Eq. 11)

Setting ∇ε(θ) = 0 gives the refined-fitting parameters θ̂_r:

2A θ̂_r = −b      (Eq. 12)

This refined solution θ̂_r is accepted if C(θ̂_r) > C(θ̂_c).

Refinement relies only on a local neighbourhood, and the neighbours for each pRF parameter remain static, so the neighbours and their corresponding design matrix for quadratic approximation are either precomputed or can be computed in parallel with the prediction signal computation. The neighbourhood data consists of only a few values, depending on the selected pRF modelling approach, so refinement can take place on both CPU and GPU.

By employing this non-iterative, quadratic approximation approach, GEM-pRF significantly reduces computation time while maintaining accurate parameter estimations.

#### 2.1.3. Variance explained

Similar to the original pRF mapping procedure proposed by Dumoulin and Wandell (2008), we incorporate a goodness-of-fit criterion. The nuisance-regressed time course y* is:

y* = [I − R R^T] y      (Eq. 13)

and the variance explained ρ² is:

ρ² = 1 − ê^T ê / (y*^T y*)
    = 1 − y^T y / (y*^T y*) + C² / (y*^T y*) + y^T R R^T y / (y*^T y*)      (Eq. 14)

### 2.2. Multiple runs

The GEM-pRF implementation uses an approach equivalent to averaging for the joint analysis of multiple runs. It extends the reformulated linear regression approach to the sum of vector projections of the measured signals against the modelled signals for individual runs, and can jointly analyse runs measured with different stimulus paradigms. For M distinct runs with orthonormal time courses p'_m(θ) and measured fMRI time courses y_m, the pRF parameters are obtained by maximising:

Σ_m y_m^T p'_m(θ)      (Eq. 15)

### 2.3. Sampling space

The coarse-fitting step involves defining a parameter set Θ used both for coarse and refined fitting. Choosing a dense sampling grid is crucial. For a 2D Gaussian pRF, the three parameters are μx, μy and σ. While these spatial parameters can be formed by a uniform grid, GEM-pRF supports complex spatial distributions (hexagonal, circular, or other shapes) via custom input parameters. The sampling space was extended beyond the stimulated visual field; for example, we set the sampling space diameter to 1.5 times that of the visual stimulus. For the GEM-pRF analyses in this work, we also adjusted the number of grid points in the spatial dimensions to maintain a spacing of 0.19° between adjacent points in each dimension.

### 2.4. Data transfer considerations

The total number of model signals depends on the defined pRF sampling space and commonly spans several hundred thousand, entailing memory necessities from several hundred megabytes to a few gigabytes (with 64-bit precision). Data must be transferred between CPU (host) and GPU (device), predominantly over the PCIe high-speed bus (Gorelick and Ozsvald, 2020), especially on low-end consumer systems. GEM-pRF minimises such transfers—for example, model signals are directly computed on the GPU side and kept there until the analysis finishes.

### 2.5. Multi-GPU environment

In a multi-GPU environment, GEM-pRF distributes the various computationally expensive and GPU memory-demanding execution steps onto different GPUs. This makes it possible to run pRF analysis with a much larger number of model signals and therefore specify denser pRF sampling space. For a multi-GPU cluster, the GPUs that are available for processing can be specified so that the program can automatically distribute memory requirements uniformly on all specified GPUs. All specified GPUs must have enough memory available for processing.

### 2.6. Data

To evaluate the accuracy of pRF parameter estimation results obtained using GEM-pRF, we employed both simulated and empirical data. For the analysis of computational times, we generated separate simulated datasets of different sizes.

#### 2.6.1. Simulated data

Simulated fMRI time series data was generated using the prfsynth docker image (version d9b64480cf1e) provided by a publicly available validation framework (Lerma-Usabiaga et al., 2020). We generated simulated fMRI time courses for three spatial locations (P, Q, and R) in the visual field. The parameters for the simulated pRF were: (μx = 0, μy = 0, σ = 1) for location P, (μx = 3, μy = 3, σ = 1) for location Q, and (μx = 6, μy = 6, σ = 1) for location R. The stimulus extended from −10 to +10 degrees visual angle. The pRF positions were chosen at different eccentricities to assess estimation accuracy between the fixation centre and the periphery close to the stimulation border. The simulated data was generated at two different white Gaussian noise levels. In the low-noise condition, the data achieved an average variance explained of 88%; in the high-noise condition, the average variance explained was 47%. We generated 5000 simulated time courses for each position.

#### 2.6.2. Empirical data

For the analysis using empirical data, we used the pre-processed New York University (NYU) retinotopy dataset (Himmelberg et al., 2021). This dataset was collected from 44 healthy young adults who completed a standard retinotopy experiment. During the experiment, participants watched visual stimulus patterns within a moving bar aperture (width 3.1°). Within this bar aperture, a stimulus pattern of colourful objects, faces, and scenes of varying scales appeared, randomly arranged on a pink-noise background. The stimulation patterns appeared within a circular window of 24.8° diameter, and the bar aperture moved across the screen 8 times, each in 24 equal steps, once per second, synchronised to the MR image acquisition. Each scan lasted 192 s, and 4 to 12 scans were collected per participant.

Data were acquired on a 3T Siemens MAGNETOM Prisma MRI scanner at the NYU Centre for Brain Imaging using a 64-channel head coil. Structural data included one or two whole-brain T1-weighted MPRAGE images per participant (TR = 2400 ms, TE = 2.4 ms, voxel size = 0.8 mm³, flip angle = 8°), and for a subset (n = 11), an additional T2-weighted scan (TR = 3200 ms, TE = 564 ms, voxel size = 0.9 mm³, flip angle = 120°). Functional data were obtained using a T2*-weighted multiband EPI sequence (TR = 1000 ms, TE = 37 ms, voxel size = 2 mm³, flip angle = 68°, multiband acceleration factor = 6, phase-encoding = posterior–anterior). Two spin-echo images were also collected for susceptibility distortion correction (AP and PA phase encoding).

Preprocessing was carried out by the dataset authors using fMRIPrep v20.0.1 (Esteban et al., 2019). Anatomical preprocessing included intensity inhomogeneity correction, skull-stripping, tissue segmentation, and cortical surface reconstruction with FreeSurfer. Functional preprocessing involved distortion correction with topup, motion correction, slice-time correction, and co-registration of functional to anatomical images, applied in a single interpolation step. The pre-processed functional data were resampled to individual cortical surfaces.

### 2.7. Validation of single-step fine fitting in GEM-pRF

Conventional analyses estimate coarse pRF parameters and then refine them through an iterative search. At the methodological level, an exhaustive iterative search can be considered the current state-of-the-art method, as it yields the most accurate refined parameters by minimising the RSS. We computed refined pRF parameter estimates using both our quadratic fitting formulation and an exhaustive iterative search implemented in SciPy (Virtanen et al., 2020), then analysed the differences. Because exhaustive iterative refinement requires impractically long computation times, this comparison was restricted to V1 of the first 22 subjects of the NYU retinotopy dataset. For fairness, both methods used the same HRF, number of regressors, and sampling space. For coarse fitting, the pRF positions were arranged on a triangular grid with a spacing of 0.165° between neighbouring points in the spatial dimensions. The same analysis was repeated with wider grid spacing (three times the spacing, 0.496°; see Supplement).

### 2.8. Comparison with state-of-the-art

We evaluated accuracy against mrVista, a widely used state-of-the-art implementation, using both simulated and empirical data.

#### 2.8.1. Comparison using simulated data

For a visual stimulus of 10° radius, we defined the sampling space spanning −15.0° to +15.0° (1.5× the stimulus radius) with 0.19° spacing, producing a spatial grid of 151 × 151. These positions were duplicated across 16 pRF sizes from 0.1° to 5°, yielding a total of 151 × 151 × 16 predicted time courses. For comparison, we computed mrVista pRF parameter estimations using the prfanalyze-vista Docker container (version 2.3.1_3.1.2; Lerma-Usabiaga et al., 2020), with its default configuration.

#### 2.8.2. Comparison using empirical data

pRF estimates were computed for V1 in the NYU dataset using mrVista's prfanalyze-vista Docker container (version 2.3.1_3.1.2; Lerma-Usabiaga et al., 2020) and GEM-pRF. Given the 24.8° diameter NYU stimulus, we defined a sampling space of 187 × 187 positions, covering −18.6° to +18.6°, with 0.19° spacing. Each spatial position was paired with 24 pRF sizes (0.2–12.4°, nonlinearly spaced), matching the pRF size sampling scheme used in mrVista. The same HRF and number of regressors as used in mrVista were applied.

### 2.9. Retinotopic maps

To visually verify the plausibility of pRF estimation results, we generated retinotopic maps (eccentricity, polar angle, and pRF size) along with the coverage map using the plotting function in github.com/dlinhardt/prfclass. The maps containing V1 were generated only for a representative subject (wlsubj001) from the NYU retinotopy dataset. These maps were derived from pRF estimates obtained through the joint analysis of 12 runs for this subject. We used the same grid configuration (187 × 187 × 24).

### 2.10. Performance analysis

Performance tests were run on two platforms: a consumer laptop (ASUS ROG x13, AMD Ryzen 9, 8 cores, 3.30 GHz, 32 GB RAM, RTX 3050 Ti, 4 GB GPU Memory) and a High-Performance Computing (HPC) system (Intel Xeon E5–2698 v4, 40 cores, 2.20 GHz, 4× NVIDIA Tesla V100 DGX, 32 GB per GPU).

Simulated fMRI datasets of different sizes (up to 100,000 voxels) were created using the validation framework (Lerma-Usabiaga et al., 2020). Ground truth parameters were μx = 0, μy = 0, σ = 1, with white noise adjusted for an overall variance explained of ~70%. Configurations evaluated:

- GEM-pRF with sampling space 151 × 151 × 16 with refine-fitting enabled on HPC
- GEM-pRF with sampling space 151 × 151 × 16 without refine-fitting on HPC
- GEM-pRF with sampling space 151 × 151 × 16 without refine-fitting on consumer laptop
- mrVista, default configuration of prfanalyze-vista (version 2.3.1_3.1.2)

## 3. Results

All analyses were computed on either a standard laptop with a GPU or a high-performance computing system with multiple GPU clusters.

### 3.1. Validation of single-step fine-fitting in GEM-pRF

Starting from identical coarse estimates, we quantified voxel-wise deviations in pRF parameters (μx, μy, σ), and variance explained (ρ²) after refinement for all voxels with at least 10% variance explained at the coarse estimates and outlier removal. Quadratic and iterative refinements yielded highly consistent outcomes, with voxel distributions tightly clustered along the identity line. Pearson's correlation coefficients were very high across all parameters (r = 0.99 for μx, r = 1.00 for μy, r = 0.97 for pRF size σ, and r = 1.00 for ρ²). With wider grid spacing (three times wider, 0.496°), noticeable deviations from the identity line and overestimates of pRF sizes were observed (see Supplementary Figure 1).

### 3.2. Comparison with state-of-the-art

#### 3.2.1. Comparison using simulated data

The simulated dataset comprised 5000 fMRI time series for three distinct spatial positions (P, Q, R). Under low noise, GEM-pRF and mrVista parameter estimates aligned closely with the ground truth for spatial positions P and Q, with minor deviations for the peripheral position R. Under high noise, both methods reliably estimated pRF parameters for P and Q but showed notable deviations for peripheral position R. Both implementations underestimated pRF sizes in the high-noise scenario; GEM-pRF results showed several fixed-size small circles at the lower sigma bound (0.1°), while mrVista showed even smaller circles. At higher eccentricities, positional errors (Δμx, Δμy) were asymmetrically larger on the positive Δ side, suggesting a systematic bias towards the periphery, more pronounced in the high-noise condition.

#### 3.2.2. Comparison using empirical data

Voxel-wise agreement between GEM-pRF and mrVista was assessed across n = 1,649,655 voxels (NYU dataset) after applying plausibility filtering: pRF centres (μx, μy) within 1.5× the stimulus radius, pRF sizes (σ) between 0 and the stimulus radius, and variance explained (ρ²) between 10 and 100%. Pearson correlations were r = 1.00 for μx, r = 1.00 for μy, r = 0.98 for σ, and r = 1.00 for ρ². Subtle banding patterns were visible along the axes for pRF centres, reflecting the discrete spatial grid used in both methods. For pRF size, mostly vertical banding up to ~4° indicated a slightly stronger tendency of mrVista to remain on the coarse grid. All comparisons used the same HRF, identical numbers of regressors, and a matched sampling space.

### 3.3. Retinotopy maps

Cortex overlays of eccentricity, polar angle and pRF size maps were presented for a representative NYU subject. The coverage map showed a higher density of mapped pRFs near the foveal region compared to the parafoveal region, with a disparity between upper and lower vertical meridians.

### 3.4. Performance analysis

For a default sampling space of 151 × 151 × 16 and a bar visual stimulus of duration 300 s and size 101 × 101, the total initialisation time was approximately 320 s on the HPC system. This initialisation is independent of dataset size and is required only once when analysing multiple datasets; it can also be cached.

Computational time increased almost linearly with fMRI dataset size. mrVista's default implementation required slightly less than 3 hours to perform pRF estimations on a dataset containing 100,000 voxels. GEM-pRF completed the same task in less than 1 minute on the HPC system and around 4 minutes on the consumer laptop using coarse-fitting only (151 × 151 × 16 sampling space), and about 2 minutes on the HPC system with both coarse and refine-fitting.

## 4. Discussion

The proposed GEM-pRF implementation introduces two novelties into retinotopic mapping: (1) a mathematical reformulation for high-speed coarse fitting, and (2) a single-step refined fitting approach using quadratic approximation. Both innovations yield considerable increases in computational efficiency while maintaining high accuracy. GEM-pRF reformulates the GLM approach into projections on prediction time courses p'(Θ) which can be computed and evaluated on the GPU, enabling accelerated execution of the coarse-fitting stage. The refinement step uses a quadratic approximation of the objective function in the neighbourhood of the coarse-fit parameter estimates, and refined pRF parameters are determined from the maximum of that approximation. The GEM-pRF implementation provides an extensive configuration file enabling researchers to specify input datasets in BIDS format and conduct pRF analysis with different settings.

### 4.1. Validation of single-step fine fitting in GEM-pRF

Starting from identical coarse fits, quadratic fitting produces parameter estimates nearly indistinguishable from those obtained through iterative procedures. Correlation values approaching unity across position, size, and explained variance confirm that quadratic refinement achieves equivalent accuracy. It does so in a single step that makes use of the coarse fitting results and eliminates computationally intensive iterative updates. Slight deviations were noticed for larger grid spacings, indicating that the quadratic approximation of the error function works best in a local neighbourhood around the coarse estimate.

### 4.2. Comparison using simulated data

Quantitative analysis using simulated data demonstrated GEM-pRF's ability to estimate pRF parameters for noisy fMRI data. Estimations for peripherally situated receptive fields (Position R) showed larger deviations from ground truth, particularly under high-noise conditions, aligning with prior findings (Lerma-Usabiaga et al., 2020). Both implementations underestimated pRF sizes in the high-noise case; GEM-pRF's small, fixed pRF sizes correspond to the lower sigma bound (0.1°) of the sampling space. Both methods achieved similar average ρ² values on these simulated voxels. The directional bias in position estimates at higher eccentricities suggests a systematic deviation in pRF localisation, potentially reflecting limitations in visual stimulation pattern or fitting procedures—warranting further investigation.

### 4.3. Comparison using empirical data

Head-to-head comparison with the established mrVista implementation reinforces GEM-pRF's validity. Using the NYU retinotopic dataset, the two methods showed virtually identical parameter estimates across more than 1.6 million voxels, with only subtle differences. Very high correlations across all parameters confirm close agreement.

### 4.4. Retinotopy maps

Cortical overlays of eccentricity, polar angle, and pRF size maps exhibit expected retinotopic organisation (Himmelberg et al., 2023; Wandell and Winawer, 2011) in an in vivo dataset. Eccentricity values increase from red to blue as we move from the posterior to the anterior end of the primary visual cortex (V1), aligning with known retinotopic organisation. The polar angle maps follow the expected visual field representation, with the left hemisphere corresponding to the right visual field and vice versa. The coverage map reveals more coverage along the lower vertical meridian as compared to the upper vertical meridian, consistent with previous studies.

### 4.5. Speed

The GEM-pRF implementation provides a speedup of almost two orders of magnitude on 100,000 voxels. Computational times on the consumer laptop are higher than those on the HPC system for a 151 × 151 × 16 sampling space without refined fitting. Matrix operations and objective function term evaluations are handled more efficiently by the DGX V100 due to its architectural optimisations for computational workloads, and data transfer between GPU and CPU contributes more to the overall runtime on the consumer laptop (PCIe bandwidth and memory access speeds).

The underlying mathematics for GEM-pRF is a reformulated version of the originally proposed pRF mapping methodology by Dumoulin and Wandell (2008). Therefore, the pRF parameters and retinotopic maps calculated with GEM-pRF are similar to those obtained by the mrVista gold-standard approach. This contrasts with some other implementations: fast-pRF (Bhat et al., 2021) uses tile coding and hashing based encoding of stimulus, without the typical GLM approach, favouring speed over accuracy and often mapping parameters on discrete grid values with significant deviations. DeepRF (Thielen et al., 2019) is a deep learning-based approach but requires substantial training time and may be limited for studies requiring different models per stimulus setup. The deep learning-based implementation by Ribeiro et al. (2021) returns estimated pRF parameters of the early visual areas without requiring functional scans, predicting retinotopy maps from anatomical brain segmentation using a geometric deep learning model trained on the Human Connectome Project (HCP) dataset (Benson et al., 2018). Its accuracy is influenced by the reliability of the pRF estimations used for training, and because it relies solely on anatomical data, it may not account for functional alterations due to visual pathway pathologies.

### 4.6. Sampling space

The refinement stage aims to enhance the accuracy of pRF parameter estimation achieved during the coarse fitting phase by exploring parameter combinations in the vicinity of the coarse-fit parameters. Selecting an adequately dense sampling space for pRF parameters is crucial. In the current work, we maintained a spatial spacing of 0.19° between adjacent grid points, then duplicated the spatial grid for different pRF sizes. GEM-pRF provides flexibility for various custom sampling configurations and accommodates complex, irregular spatial patterns of receptive fields.

### 4.7. Joint analysis

It is customary in pRF analysis to perform joint analysis of multiple datasets, obtained during different runs, sessions, or with different visual stimuli for a subject. GEM-pRF provides an out-of-the-box software implementation for such joint analyses.

### 4.8. Scalability

GEM-pRF employs a batching procedure to handle memory-intensive execution steps on GPUs. Since the estimation of pRF parameters for each voxel's fMRI time series y is independent, the minimum batch size can even be reduced to a single voxel. However, during coarse fitting, the vector projection of a voxel's fMRI time series y is computed with respect to all prediction time courses, so the current implementation requires holding all prediction time series data in GPU memory. The user must select a sampling space Θ configuration such that the prediction time courses fit in available GPU memory.

### 4.9. Future scope of work

The modular, generic development approach for the GEM-pRF implementation paves the way for future advancements. The software currently uses a 2D Gaussian model, with potential to incorporate alternatives such as the Difference of Gaussians (Zuiderbaan et al., 2012). The implementation already provides a framework of abstract classes for integrating new pRF modelling approaches. Further performance improvements can be explored, such as leveraging CUDA streams to achieve additional parallelisation in CPU–GPU data transfer and processing.

## 5. Conclusion

We introduced a novel mathematical solution that reworks the design matrix using orthogonalization, allowing us to compute the objective function and its derivatives directly on the GPU using vector projections. Our approach also eliminates the need for iterative refinement, making the process significantly faster with high accuracy. Our software implementation GEM-pRF yielded accurate pRF mapping results in a fraction of the computation time required with the gold-standard mrVista software package. The implementation offers a modular and flexible approach for efficiently analysing large fMRI datasets with varying configurations. Notably, the software's scalability allows for effective handling of memory-intensive computations, while its performance surpasses that of widely used tools without sacrificing accuracy. As the first GPU-accelerated implementation utilising the traditional GLM-based fitting approach for visual field mapping, GEM-pRF offers a significant step forward in computational neuroimaging.

## Code availability

- PyPI: https://pypi.org/project/gemprf/
- Demo kit: https://github.com/siddmittal/GEMpRF-DemoKit

## Funding

Austrian Science Fund (FWF; grant https://doi.org/10.55776/P35583).

## Key visual area references

- V1, V2, VP, V3, V4 (Sereno et al., 1995): Introduction cites Sereno et al.'s functional segmentation of these visual area regions on the cortical surface using fMRI-based retinotopic mapping with periodic visual stimulation.
- V1 (primary visual cortex): Used as the region-of-interest for the validation of single-step fine fitting (Section 2.7 and 3.1) — comparison restricted to V1 of the first 22 NYU retinotopy subjects; used as the ROI for the empirical comparison against mrVista in Section 2.8.2; retinotopic maps (Section 2.9 and 3.3) showing eccentricity, polar angle, and pRF size were generated for V1 of representative subject wlsubj001.
- V1, V2, V3 (Benson et al., 2022): Referenced citation "Variability of the Surface Area of the V1, V2, and V3 Maps in a Large Sample of Human Observers."
