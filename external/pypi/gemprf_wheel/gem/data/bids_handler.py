# -*- coding: utf-8 -*-
"""

"@Author  :   Siddharth Mittal",
"@Version :   1.0",
"@Contact :   siddharth.mittal@meduniwien.ac.at",
"@License :   (C)Copyright 2024 - 2025, Medical University of Vienna",
"@Desc    :   None",
        
"""

import json
import os
import re
import sys

from gem.data.diagnostic_bids_tree import DiagnosticBidsTree
from gem.data.gem_bids_concatenation_data_info import BidsConcatenationDataInfo
from gem.data.gem_stimulus_file_info import StimulusFileInfo
from gem.utils.logger import Logger

class GemBidsHandler:
    @classmethod
    def __get_stimulus_file_info(cls, stimulus_dir : str, stimulus_filename : str):
        match = re.search(r'task-([a-zA-Z0-9\-]+)', stimulus_filename) # regex to extract task name even if it contains hyphens
        if match:
            stimulus_task = match.group(1)
        else:
            raise ValueError(f"Stimulus Task name not found in the stimulus file name: {stimulus_filename}")
        
        stimulus_info = StimulusFileInfo(stimulus_dir, stimulus_filename, stimulus_task)
        return stimulus_info
    
    @classmethod
    def extract_value_from_bids_string(cls, bids_format_string : str, key :str):
        parts = bids_format_string.split('_')
        for part in parts:
            if '-' in part:
                found_key, found_value = part.split('-', 1) # split only on the first hyphen
                if found_key == key: