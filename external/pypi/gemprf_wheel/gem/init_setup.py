def set_system_gpus(max_available_gpus):
    all_gpus_list = list(range(max_available_gpus))
    all_gpus_str = ','.join(map(str, all_gpus_list))
    os.environ["CUDA_VISIBLE_DEVICES"] = all_gpus_str

def manage_gpus(cfg, max_available_gpus):
    try:
        custom_default_gpu_id = int(cfg.gpu.get("default_gpu"))
    except Exception:
        raise ValueError(
            "Invalid GPU configuration: the 'default_gpu' value must be an integer. \nSee https://gemprf.github.io/")

    # Optional additional GPUs
    additional_node = cfg.gpu.get("additional_available_gpus")

    if additional_node and "gpu" in additional_node:
        additional_gpus = additional_node["gpu"]

        # Handle single <gpu> vs multiple <gpu>
        if not isinstance(additional_gpus, list):
            additional_gpus = [additional_gpus]

        other_available_gpus = sorted({int(g) for g in additional_gpus if int(g) != custom_default_gpu_id})
    else:
        other_available_gpus = []
        max_available_gpus > 1 and Logger.print_blue_message("Note: Multi-GPU is supported, but none were specified. Using the specified default GPU.", print_file_name=False)

    user_specified_gpus_list = [custom_default_gpu_id] + other_available_gpus

    # Sanity check
    if not all(0 <= gpu_id < max_available_gpus for gpu_id in user_specified_gpus_list):
        raise ValueError(f"GPU IDs must be in range [0, {max_available_gpus - 1}].")

    os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, user_specified_gpus_list))


def run_selected_program(selected_program, config_filepath):
    cfg = GEMpRFAnalysis.load_config(config_filepath=config_filepath) # load default config

    # NOTE: match versions
    config_file_version = cfg.config_data["@version"]
    if config_file_version != __version__:
        Logger.print_red_message(
            f"Version mismatch: config={config_file_version}, GEMpRF={__version__}. "
            "\nDownload matching versions at: https://gemprf.github.io/",
            print_file_name=False
        )
        sys.exit(1)        
    print(f"GEMpRF version: {__version__}")

    # read user defined spatial points, if any
    spatial_points_xy = None
    if cfg.optional_analysis_params['enable'] and cfg.optional_analysis_params['spatial_grid_xy']['use_from_file']:
        spatial_points_xy = H5FileManager.get_key_value(filepath=cfg.optional_analysis_params['filepath'], key = cfg.optional_analysis_params['spatial_grid_xy']['key'])
        if spatial_points_xy is None:
            Logger.print_red_message(f"Could not load spatial grid points from file: {cfg.optional_analysis_params['filepath']} with key: {cfg.optional_analysis_params['spatial_grid_xy']['key']}", print_file_name=False)
            sys.exit(1)

    # GPUs management
    #...get max. number of available GPUs without using cuda
    pynvml.nvmlInit()
    max_available_gpus = pynvml.nvmlDeviceGetCount() #cp.cuda.runtime.getDeviceCount()
    pynvml.nvmlShutdown()
    try:
        manage_gpus(cfg, max_available_gpus)
    except ValueError as e:
        Logger.print_red_message(f"GPU config error: {e} Utilizing all available GPUs...", print_file_name=False)
        set_system_gpus(max_available_gpus)
    _ = ggm(default_gpu_id = 0) # Here "0" reresents the index in "os.environ["CUDA_VISIBLE_DEVICES"]", which will automatically be the correct one

    # copy the config file to the results folder, decide to overwrite or not the existing analysis results diretory
    if selected_program == SelectedProgram.GEMAnalysis:
        if cfg.bids['@enable'] == "True":
            result_dir = os.path.join(cfg.bids.get("basepath"), "derivatives", "prfanalyze-gem", f'analysis-{cfg.bids["results_anaylsis_id"]["#text"]}')
        else:
            result_dir = cfg.fixed_paths['results']['basepath']
        if os.path.exists(result_dir) and cfg.bids["results_anaylsis_id"].get("@overwrite").lower() == "false":
            shutil.move(result_dir, f'{result_dir}_backup-{datetime.datetime.now():%Y%m%d-%H%M%S}')
        shutil.copy(config_filepath, result_dir) if os.makedirs(result_dir, exist_ok=True) is None else None

    # ...prf spatial points
    if spatial_points_xy is None:
        if selected_program == SelectedProgram.GEMAnalysis:
            spatial_points_yx = GEMpRFAnalysis.get_prf_spatial_points(cfg) # this will return the spatial points in (row/y, col/x) format

        # convert spatial points from (row, col) to (col, row)
        spatial_points_xy = spatial_points_yx
        spatial_points_xy = spatial_points_yx[:, [1, 0]]

    # selected pRF model
    selected_prf_model = GEMpRFAnalysis.get_selected_prf_model(cfg)                
    if selected_prf_model == SelectedPRFModel.GAUSSIAN:             
        prf_model = PRFGaussianModel(visual_field_radius= np.max(spatial_points_xy)) 

    # additional dimensions
    if selected_program == SelectedProgram.GEMAnalysis:
        additional_dimensions = GEMpRFAnalysis.get_additional_dimensions(cfg, selected_prf_model)
        
    prf_space = PRFSpace(spatial_points_xy, additional_dimensions=additional_dimensions)
    prf_space.convert_spatial_to_multidim()