# -*- coding: utf-8 -*-

"""
"@Author  :   Siddharth Mittal",
"@Version :   1.0",
"@Contact :   siddharth.mittal@meduniwien.ac.at",
"@License :   (C)Copyright 2024-2025, Siddharth Mittal",
"@Desc    :   None",     
"""

import math
import os
import sys
from typing import List
import numpy as np
import cupy as cp
import matplotlib.pyplot as plt
from enum import Enum

from gem.model.selected_prf_model import SelectedPRFModel
from gem.model.prf_stimulus import Stimulus
from gem.model.prf_model import PRFModel
from gem.space.PRFSpace import PRFSpace
from gem.model.prf_model import GaussianModelParams
from gem.model.prf_model import DoGModelParams
from gem.utils.hpc_cupy_utils import HpcUtils as gpu_utils
from gem.utils.gem_write_to_file import GemWriteToFile
from gem.utils.logger import Logger
from gem.utils.gem_gpu_manager import GemGpuManager as ggm

DEBUG = False

class SignalSynthesizer:
    @classmethod
    def __set_kernel_config(self, num_xThreads : int, num_yThreads : int, num_zThreads : int):
        block_dim = (512, 1, 1)
        bx = int((num_xThreads + block_dim[0] - 1) / block_dim[0])
        by = int((num_yThreads + block_dim[1] - 1) / block_dim[1])
        bz = int((num_zThreads + block_dim[2] - 1) / block_dim[2])
        grid_dim = (bx, by, bz)
        return block_dim, grid_dim

    """Compute the model curves (Gaussian curves, DoG curves, etc.) based on the selected PRF model"""
    @classmethod
    def compute_signals_on_gpu(cls,
                               model_type: SelectedPRFModel,
                               stimulus_data_selected_gpu : cp.ndarray,
                               stimulus_x_range : cp.ndarray,
                               stimulus_y_range : cp.ndarray,
                               stimulus_height : int,
                               stimulus_width : int,
                               cuda_kernel: cp.RawKernel,
                               multi_dim_points_gpu: cp.ndarray,
                               num_dimension: int) -> cp.ndarray:
        # one curve for each point
        num_model_curves = len(multi_dim_points_gpu)
        # these are just the model curves (e.g. gaussian, DoG etc.)
        result_model_curves_gpu = cp.zeros((num_model_curves * stimulus_height * stimulus_width), dtype=cp.float64)

        # we may have more than 3 dimensions, we need to flatten out data, each cuda thread responsible to compute a model curve for a single point
        # sample points data [(0, 0, 1, 2), (-9, -9, 8, 5).....]
        flattened_points_gpu = multi_dim_points_gpu.ravel()

        # call the CUDA kernel
        block_dim, grid_dim = SignalSynthesizer.__set_kernel_config(num_xThreads=num_model_curves, num_yThreads=1, num_zThreads=1)
        cuda_kernel(grid_dim, block_dim,
                    (result_model_curves_gpu,
                     flattened_points_gpu,
                     stimulus_x_range,
                     stimulus_y_range,
                     num_dimension,
                     stimulus_height,
                     stimulus_width,
                     num_model_curves))

        # each row contains a flat model curve for a single point (e.g. gaussian curve for a single point)
        model_curves_rm_gpu = result_model_curves_gpu.reshape(
            (num_model_curves, stimulus_height * stimulus_width))
        # stimulus data is column major
        signal_rowmajor_gpu = cp.dot(model_curves_rm_gpu, stimulus_data_selected_gpu)

        if (DEBUG):
            if (True):                
                # plot the model curves
                #...plot pRF
                gc = cp.asnumpy(model_curves_rm_gpu)
                center_gc_idx = int(num_model_curves // 2) #...if you want center pRF
                gc_idx = 20
                pRF = (cp.asnumpy(gc[gc_idx, :])).reshape((101, 101))
                maxEcc_dummy = 9.0 # 13.5
                fig, ax = plt.subplots()
                ax.imshow(pRF, cmap='hot', origin='lower', extent=(-maxEcc_dummy, maxEcc_dummy, -maxEcc_dummy, maxEcc_dummy))
                ax.set_xlabel('X')
                ax.set_ylabel('Y')
                ax.set_title('pRF')
                ax.set_xticks([-maxEcc_dummy, 0, maxEcc_dummy]) # NOTE: hardcorded value for plot, maxEcc_dummy = 13.5
                ax.set_yticks([-maxEcc_dummy, 0, maxEcc_dummy])
                plt.show()

                # plot the signal
                plt.figure()
                plt.plot(cp.asnumpy(signal_rowmajor_gpu[center_gc_idx, :]))
                Logger.print_red_message(
                    message="GEM-WARNING: Turn off the debug flag.")

        return signal_rowmajor_gpu
    
    @classmethod
    def get_stimulus_data_on_selected_gpu(cls, stimulus : Stimulus, selected_device_id : int):
        # transfer stimulus data on the selected device, if the selecte device is not 0
        if(ggm.get_instance().default_gpu_id != selected_device_id):
            with cp.cuda.Device(selected_device_id):
                stimulus_data_selected_gpu = cp.asarray(stimulus.stimulus_data_cpu)
                stimulus_x_range = cp.asarray(stimulus.x_range_cpu)
                stimulus_y_range = cp.asarray(stimulus.y_range_cpu)
        else:
            stimulus_data_selected_gpu = stimulus.stimulus_data_gpu
            stimulus_x_range = stimulus.x_range_gpu
            stimulus_y_range = stimulus.y_range_gpu
