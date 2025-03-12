#!/usr/bin/env python
'''
Before running:
module load aretomo3 miniconda/cryocare

Run this script in the following folder structure:

project/
+- raw/
¦  +- tomo200528_100.mrc.mdoc
¦  +- tomo200528_100_0.0_May30_22.19.28.tif
¦  +- tomo200528_100_3.0_May30_22.20.54.tif
¦  +- ...
¦  +- tomo200528_110.mrc.mdoc
¦  +- tomo200528_110_0.0_May30_22.19.28.tif
¦  +- tomo200528_110_3.0_May30_22.20.54.tif
¦  +- etc...

This script will modify it with the following output:

project/
+- raw/
¦  +- tomo200528_100.mrc.mdoc
¦  +- tomo200528_100_0.0_May30_22.19.28.tif
¦  +- tomo200528_100_3.0_May30_22.20.54.tif
¦  +- ...
¦  +- tomo200528_110.mrc.mdoc
¦  +- tomo200528_110_0.0_May30_22.19.28.tif
¦  +- tomo200528_110_3.0_May30_22.20.54.tif
¦  +- etc...
+- AreTomo3Output/
¦  +- AreTomo3_Session.json
¦  +- MdocDone.txt
¦  +- TiltSeries_Metric.csv
¦  +- tomo200528_100.mrc.aln
¦  +- tomo200528_100.mrc_TLT.txt
¦  +- tomo200528_100.mrc_Log
¦  +- tomo200528_100.mrc_CTF_Imod.txt
¦  +- tomo200528_100.mrc_CTF.mrc
¦  +- tomo200528_100.mrc_CTF.txt
¦  +- tomo200528_100.mrc_EVN.mrc
¦  +- tomo200528_100.mrc_EVN_Vol.mrc
¦  +- tomo200528_100.mrc_ODD.mrc
¦  +- tomo200528_100.mrc_ODD_Vol.mrc
¦  +- tomo200528_100.mrc.mrc
¦  +- tomo200528_100.mrc_Vol.mrc
¦  +- ...
¦  +- tomo200528_110.mrc.aln
¦  +- tomo200528_110.mrc_TLT.txt
¦  +- tomo200528_110.mrc_Log
¦  +- tomo200528_110.mrc_CTF_Imod.txt
¦  +- tomo200528_110.mrc_CTF.mrc
¦  +- tomo200528_110.mrc_CTF.txt
¦  +- tomo200528_110.mrc_EVN.mrc
¦  +- tomo200528_110.mrc_EVN_Vol.mrc
¦  +- tomo200528_110.mrc_ODD.mrc
¦  +- tomo200528_110.mrc_ODD_Vol.mrc
¦  +- tomo200528_110.mrc.mrc
¦  +- tomo200528_110.mrc_Vol.mrc
+- tomograms/
¦  +- even/
¦  ¦  +- tomo200528_100.mrc (symlink to tomo200528_100.mrc_EVN_Vol.mrc)
¦  ¦  +- ...
¦  ¦  +- tomo200528_110.mrc (symlink to tomo200528_110.mrc_EVN_Vol.mrc)
¦  +- odd/
¦  ¦  +- tomo200528_100.mrc (symlink to tomo200528_100.mrc_ODD_Vol.mrc)
¦  ¦  +- ...
¦  ¦  +- tomo200528_110.mrc (symlink to tomo200528_110.mrc_ODD_Vol.mrc)
¦  +- denoised/
¦  ¦  +- tomo200528_100.mrc
¦  ¦  +- tomo200528_110.mrc
¦  +- cryocare_model/
'''
import subprocess
import argparse
import pathlib
import sys
import json
import numpy as np

ARETOMO_CMD = 'aretomo3'

cryocare_train_data_config = {
  "even": [],
  "odd": [],
  "patch_shape": [
    72,
    72,
    72
  ],
  "num_slices": 1200,
  "split": 0.9,
  "tilt_axis": "Y",
  "n_normalization_samples": 500,
  "path": None,
  "overwrite": "True"
}

cryocare_train_config = {
  "train_data": None,
  "epochs": 100,
  "steps_per_epoch": 200,
  "batch_size": 16,
  "unet_kern_size": 3,
  "unet_n_depth": 3,
  "unet_n_first": 16,
  "learning_rate": 0.0004,
  "model_name": None,
  "path": None,
  "overwrite": "True",
  "gpu_id": None
}

cryocare_predict_config = {
  "path": None,
  "even": None,
  "odd": None,
  "n_tiles": [2,4,2],
  "output": None,
  "overwrite": "True",
  "gpu_id": None
}


class Project:
    def __init__(self, project_path, pixel_size):
        self.project_main = project_path
        self.project_raw = project_path.joinpath('raw')
        self.pixel_size = pixel_size
        if not self.project_raw.exists():
            print('no folder with raw data in project')
            sys.exit(0)
        # list mdoc files
        self.mdocs = [x for x in self.project_raw.iterdir() if x.is_file() and x.suffix == '.mdoc']
        
        # other dirs
        self.project_AreTomo3 = project_path.joinpath('AreTomo3Output')
        self.project_tomograms = project_path.joinpath('tomograms')
        self.tomos_even = self.project_tomograms.joinpath('even')
        self.tomos_odd = self.project_tomograms.joinpath('odd')
        self.tomos_denoised = self.project_tomograms.joinpath('denoised')
        self.cryocare_folder = self.project_tomograms.joinpath('cryocare_model')
    
    def aretomo(self, pixel_size, kV, cs, fm_dose, gpu_ids, gain_ref, tilt_axis, align_z, vol_z, binning, out_imod=0,
                defect_file=None):
        self.project_AreTomo3.mkdir(exist_ok=True)
        self.project_tomograms.mkdir(exist_ok=True)
        self.tomos_odd.mkdir(exist_ok=True)
        self.tomos_even.mkdir(exist_ok=True)
        # Input to required:
        # pixel_size
        # kV
        # cs
        # fm_dose
        # gpu id(s)
        # Gain ref
        # tilt_axis, TODO: see if header default is sane
        # align_z
        # vol_z
        # binning
        # out_imod (default 0)
        # (optional) defect_file
        args = [ARETOMO_CMD,
                '-InPrefix raw/', #look in raw directory
                '-InSuffix .mdoc', # look for .mdoc files
                '-OutDir AreTomo3Output', # output dir
                f'-PixSize {pixel_size}', # pixel size of input
                f'-kV {kV}', # voltage
                f'-Cs {cs}', # Spherical Aberration
                f'-FmDose {fm_dose}', #Dose per frame
                '-Cmd 0', # do full reconstructions from tilts
                f'-Gpu {gpu_ids}',
                f'-DefectFile {defect_file}' if defect_file is not None else '',
                f'-Gain {gain_ref}'
                '-InFmMotion 1', # account for inframe motion
                f'-TiltAxis {tilt_axis}', #Tilt axis TODO: see if header default is sane
                f'-AlignZ {align_z}', # Alignment z-shape
                f'-VolZ {vol_z}', # reconstructed volume z-height
                f'-AtBin {binning}', # reconstruction binning
                '-FlipVol 1', # make output vol xyz instead of xzy
                '-Wbp 1', # enable weighted back projection
                #'-DarkTol 0.01', # make dark tolerance less restrictive
                '-OutImod {out_imod}', # see aretomo3 --help
                ]
        subprocess.run(' '.join(args), shell=True)

    def create_symlinks(self): 
        # Symlink the odd and even tomograms to the correct folder
        args = ['ln', '-rs', 'AreTomo3Output/*EVN_Vol.mrc', 'tomograms/even']
        subprocess.run(' '.join(args), shell=True)
        args = ['ln', '-rs', 'AreTomo3Output/*ODD_Vol.mrc', 'tomograms/odd']
        subprocess.run(' '.join(args), shell=True)
        # rename all the files
        args = ['rename', 'mrc_EVN_Vol.mrc', 'mrc' 'tomograms/even/*']
        subprocess.run(' '.join(args), shell=True)
        args = ['rename', 'mrc_ODD_Vol.mrc', 'mrc' 'tomograms/odd/*']
        subprocess.run(' '.join(args), shell=True)
 
            
    def cryocare(self, training_subset_size, cryocare_model_name, gpu_id):
        self.cryocare_folder.mkdir(exist_ok=True)
        self.tomos_denoised.mkdir(exist_ok=True)
        train_data_file = self.project_main.joinpath('train_data_config.json')
        train_file = self.project_main.joinpath('train_config.json')
        predict_file = self.project_main.joinpath('predict_config.json')
        
        # select subset size indices
        subset = np.random.choice(len(self.mdocs), training_subset_size, replace=False)
        cryocare_train_data_config['path'] = str(self.cryocare_folder)
        # use the fact that the stem of tomoXXX.mrc.mdoc is tomoXXX.mrc
        tomos_even = [str(self.tomos_even / self.mdocs[i].stem) for i in subset]
        tomos_odd = [str(self.tomos_odd / self.mdocs[i].stem) for i in subset]

        cryocare_train_data_config['even'] = tomos_even
        cryocare_train_data_config['odd'] = tomos_odd
        with open(train_data_file, 'w') as js_file:
            js_file.write(json.dumps(cryocare_train_data_config, indent=2))
            
        # create training json
        cryocare_train_config['train_data'] = str(self.cryocare_folder)
        cryocare_train_config['path'] = str(self.cryocare_folder)
        cryocare_train_config['model_name'] = cryocare_model_name
        cryocare_train_config['gpu_id'] = gpu_id
        with open(train_file, 'w') as js_file:
            js_file.write(json.dumps(cryocare_train_config, indent=2))
        
        # create predict config
        cryocare_predict_config['path'] = str(self.cryocare_folder.joinpath(cryocare_model_name + '.tar.gz'))
        cryocare_predict_config['even'] = str(self.tomos_even)
        cryocare_predict_config['odd'] = str(self.tomos_odd)
        cryocare_predict_config['output'] = str(self.tomos_denoised)
        cryocare_predict_config['gpu_id'] = gpu_id
        with open(predict_file, 'w') as js_file:
            js_file.write(json.dumps(cryocare_predict_config, indent=2))
            
        # run cryocare
        subprocess.run(f'cryoCARE_extract_train_data.py --conf {train_data_file}', shell=True)
        subprocess.run(f'cryoCARE_train.py --conf {train_file}', shell=True)
        subprocess.run(f'cryoCARE_predict.py --conf {predict_file}', shell=True)
        
            
    def run(self, gain_file, defect_file, pixel_size, kV, cs, fm_dose, tilt_axis, vol_z, align_z, binning, 
            out_imod, training_subset_size, cryocare_model_name, gpu_id):
        # run aretomo
        self.aretomo(pixel_size, kV, cs, fm_dose, gpu_id, gain_file, tilt_axis, align_z, vol_z,
                     binning, out_imod, defect_file)        
        # create symlinks
        self.create_symlinks()

        # run cryocare
        self.cryocare(training_subset_size, cryocare_model_name, gpu_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start from raw tilts. Correct with MotionCor2 and create even/odd summed frames. '
        'Combine to .st and .rawtlt, then run AreTomo to make a full and even/odd reconstruction. '
        'Finally train cryocare on subset of randomly selected tomograms. ')
    parser.add_argument('--project-dir', type=str, required=False, default='./',
                        help='project directory')
    parser.add_argument('--gain-file', type=str, required=False,
                        help='gain file that is given to AreTomo3')
    parser.add_argument('--defect-file', type=str, required=False,
                        help='(Optional) Defect file that is given to AreTomo3')
    parser.add_argument('--pixel-size', type=float, required=True,
                        help='specify the pixel size so mrcs can be annotated correctly')
    parser.add_argument('--kV', type=float, required=False, default=300,
                        help='High tension in kV for dose weighting, default 300')
    parser.add_argument('--cs', type=float, required=True,
                        help='Spherical aberration in mm for CTF estimation')
    parser.add_argument('--fm-dose', type=float, required=True,
                        help='Per frame dose in e/A2.')
    parser.add_argument('--tilt-axis', type=float, required=False,
                        help='tilt axis value for aretomo')


    # both pixel size and tilt-axis can be read from the mdoc file
    # there is also pip package for reading mdoc files
    parser.add_argument('--tomogram-binning', type=int, required=False, default=8,
                        help='tomogram binning')
    parser.add_argument('--aretomo-vol-z', type=int, required=True,
                        help='tomogram reconstruction thickness before binning (in voxels)')
    parser.add_argument('--aretomo-align-z', type=int, required=True,
                        help='tomogram thickness before binning (in voxels) used to optimize tilt alignment in aretomo')
    parser.add_argument('--aretomo-tiltcor', type=int, required=False, default=0,
                        help='tiltcor for aretomo, options include -1, 0, 1 (see aretomo manual)')
    parser.add_argument('--aretomo-outimod', type=int, required=False, default=0,
			help='outimod option for aretomo, 0 (default) does not produce any imod output, '
   			     'other options are 1,2,3 (see aretomo manual)')
    parser.add_argument('--aretomo-tiltcor-angle', type=float, required=False,
                        help='angle for aretomo tiltcor (see aretomo manual)')
    parser.add_argument('--training-size', type=int, required=False, default=5,
                        help='number of tomograms to pass to cryocare for training')
    parser.add_argument('--cryocare-model-name', type=str, required=True,
                        help='give a name to your cryocare model, for example arctica_er_microsomes or krios_lamellae_yeast')
    parser.add_argument('--gpu-id', type=int, required=False, default=0,
                        help='specify the gpu index to run on')
    args = parser.parse_args()
    
    project_path = pathlib.Path(args.project_dir)
    if not project_path.is_dir():
        print('project directory does not exist')
        sys.exit(0)
    
    if args.gain_file is not None:
        gain_file = pathlib.Path(args.gain_file)
        if not gain_file.is_file():
            print('invalid gain file')
            sys.exit(0)
    else:
        gain_file = None
    
    if args.defect_file is not None:
        defect_file = pathlib.Path(args.defect_file)
        if not defect_file.is_file():
            print('invalid defect file')
            sys.exit(0)
    else:
        defect_file = None
    
    project = Project(project_path, args.pixel_size)
    project.run(gain_file, defect_file, args.pixel_size, args.kV, args.cs, args.fm_dose, args.tilt_axis,
                args.aretomo_vol_z, args.aretomo_align_z, args.tomogram_binning, args.aretomo_outimod,
                args.training_size, args.cryocare_model_name, args.gpu_id)
	
