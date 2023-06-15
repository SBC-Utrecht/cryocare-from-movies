#!/usr/bin/env python
'''
Before running:
module load motioncor2 aretomo miniconda/cryocare

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
+- stacks/
¦  +- tomo200528_100.st
¦  +- tomo200528_100_odd.st
¦  +- tomo200528_100_even.st
¦  +- tomo200528_100.rawtlt
¦  +- tomo200528_110.st
¦  +- tomo200528_110_odd.st
¦  +- tomo200528_110_even.st
¦  +- tomo200528_110.rawtlt
+- tomograms/
¦  +- full/
¦  ¦  +- tomo200528_100.mrc
¦  ¦  +- tomo200528_100.aln
¦  ¦  +- tomo200528_110.mrc
¦  ¦  +- tomo200528_110.aln
¦  +- even/
¦  ¦  +- tomo200528_100.mrc
¦  ¦  +- tomo200528_110.mrc
¦  +- odd/
¦  ¦  +- tomo200528_100.mrc
¦  ¦  +- tomo200528_110.mrc
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
import mrcfile
import numpy as np
from operator import itemgetter


MOTIONCOR2_CMD = 'motioncor2'
ARETOMO_CMD = 'aretomo'

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


def parse_mdoc(mdoc_file):
    tilt_series_name = None
    subframe_list = []
    tilt_angle_list = []    
    with open(mdoc_file, 'r') as infile:
        lines = infile.readlines()
        for x in lines:
            line = x.strip()
            if line.startswith('ImageFile'):
                tilt_series_name = line.split('=')[1].strip()
            elif line.startswith('SubFramePath'):
                subframe_list.append(line.split('=')[1].strip())
            elif line.startswith('TiltAngle'):
                tilt_angle_list.append(float(line.split('=')[1].strip()))
    return tilt_series_name, subframe_list, tilt_angle_list


def create_stack(tilt_images, outname, pixel_size):
    with mrcfile.new(outname, overwrite=True) as newstack:
        images = [mrcfile.read(x) for x in tilt_images]
        newstack.set_data(np.stack(images, axis=0))
        newstack.voxel_size = pixel_size


def create_tilt_file(tilt_angles, outname):
    with open(outname, 'w') as f:
        f.writelines([str(x) + '\n' for x in tilt_angles])
        
        
def normalise(mrc_path):
    with mrcfile.open(mrc_path, mode='r+') as tomo:
        tomo.data[:] = tomo.data / tomo.data.std()
        tomo.update_header_from_data()
        tomo.update_header_stats()


class TiltSeries:
    def __init__(self, mdoc_path):
        self.mdoc_path = mdoc_path
        self.series_name, subframes, self.tilt_angles = parse_mdoc(self.mdoc_path)
        self.series_name = self.series_name.strip('.mrc')
        self.subframes = []
        for subframe in subframes:
            # make pure windows path to find tif or eer file name
            self.subframes.append(self.mdoc_path.parent.joinpath(pathlib.PureWindowsPath(subframe).name))
        self.corrected_frames = []
        self.corrected_frames_even = []
        self.corrected_frames_odd = []
        self.full_stack = None
        self.even_stack = None
        self.odd_stack = None
        self.rawtlt_file = None
        self.tomo_full = None
        self.tomo_even = None
        self.tomo_odd = None
        self.tilt_alignment = None
            
    def motion_correction(self, gain_file, gpu_id):
        for subframe in self.subframes:
            if subframe.suffix == '.eer':
                subframe = subframe.with_suffix('.tif')
            if not subframe.exists():
                print(f'tif does not exist {subframe}, cannot continue')
                sys.exit(0)
            
            raw_dir, frame_id = subframe.parent, subframe.stem
            frame_sum = raw_dir.joinpath(frame_id + '_motcor.mrc')
            frame_sum_even = raw_dir.joinpath(frame_id + '_motcor_EVN.mrc')
            frame_sum_odd = raw_dir.joinpath(frame_id + '_motcor_ODD.mrc')
            
            args = [MOTIONCOR2_CMD, f'-InTiff {subframe}', f'-OutMrc {frame_sum}', f'-Gpu {gpu_id}', 
                    '-SplitSum 1'] + ([f'-Gain {gain_file} '] if gain_file is not None else [])
            subprocess.run(' '.join(args), shell=True)
                
            self.corrected_frames.append(frame_sum)
            self.corrected_frames_even.append(frame_sum_even)
            self.corrected_frames_odd.append(frame_sum_odd)
            
    def to_stacks(self, stacks_path, pixel_size):
        # order stacks by tilt angle first
        l = sorted(zip(self.tilt_angles, self.corrected_frames, 
                       self.corrected_frames_even, self.corrected_frames_odd), key=itemgetter(0))
        self.tilt_angles, self.corrected_frames, self.corrected_frames_even, self.corrected_frames_odd = zip(*l)
        
        # then write everything
        self.full_stack = stacks_path.joinpath(self.series_name + '.st')
        self.even_stack = stacks_path.joinpath(self.series_name + '_even.st')
        self.odd_stack = stacks_path.joinpath(self.series_name + '_odd.st')
        self.rawtlt_file = stacks_path.joinpath(self.series_name + '.rawtlt')
        create_stack(self.corrected_frames, self.full_stack, pixel_size)
        create_stack(self.corrected_frames_even, self.even_stack, pixel_size)
        create_stack(self.corrected_frames_odd, self.odd_stack, pixel_size)
        create_tilt_file(self.tilt_angles, self.rawtlt_file)
        
    def reconstruction(self, full_path, even_path, odd_path, tilt_axis, 
                       vol_z, align_z, binning, tiltcor, tiltcor_angle, gpu_id):
        self.tomo_full = full_path.joinpath(self.series_name + '.mrc')
        self.tilt_alignment = full_path.joinpath(self.series_name + '.st.aln')
        self.tomo_even = even_path.joinpath(self.series_name + '.mrc')
        self.tomo_odd = odd_path.joinpath(self.series_name + '.mrc')
        
        args = [ARETOMO_CMD, f'-InMrc {self.full_stack}', f'-AngFile {self.rawtlt_file}',
                f'-OutMrc {self.tomo_full}', f'-VolZ {vol_z}', f'-AlignZ {align_z}', f'-OutBin {binning}', 
                '-DarkTol 0.01', '-FlipVol 1', '-Wbp 1', 
                f'-TiltCor {tiltcor} ' + (str(tiltcor_angle) if tiltcor_angle is not None else ''),
                f'-Gpu {gpu_id}'] + ([f'-TiltAxis {tilt_axis}'] if tilt_axis is not None else [])
        subprocess.run(' '.join(args), shell=True)
        
        args_even = [ARETOMO_CMD, f'-InMrc {self.even_stack}', f'-OutMrc {self.tomo_even}', 
                     f'-VolZ {vol_z}', '-OutBin 8', '-FlipVol 1', '-Wbp 1', 
                     f'-AlnFile {self.tilt_alignment}', f'-Gpu {gpu_id}']
        subprocess.run(' '.join(args_even), shell=True)
        
        args_odd = [ARETOMO_CMD, f'-InMrc {self.odd_stack}', f'-OutMrc {self.tomo_odd}', 
                     f'-VolZ {vol_z}', '-OutBin 8', '-FlipVol 1', '-Wbp 1', 
                     f'-AlnFile {self.tilt_alignment}', f'-Gpu {gpu_id}']
        subprocess.run(' '.join(args_odd), shell=True)
        
        # normalise tomograms after aretomo to std=1
        normalise(self.tomo_full)
        normalise(self.tomo_even)
        normalise(self.tomo_odd)


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
        self.tilt_series = [TiltSeries(x) for x in self.mdocs]
        
        # other dirs
        self.project_stacks = project_path.joinpath('stacks')
        self.project_tomograms = project_path.joinpath('tomograms')
        self.tomos_full = self.project_tomograms.joinpath('full')
        self.tomos_even = self.project_tomograms.joinpath('even')
        self.tomos_odd = self.project_tomograms.joinpath('odd')
        self.tomos_denoised = self.project_tomograms.joinpath('denoised')
        self.cryocare_folder = self.project_tomograms.joinpath('cryocare_training')
    
    def motioncor2(self, gain_file, gpu_id):
        for ts in self.tilt_series:
            print(f'motioncor2 for {ts.series_name}')
            ts.motion_correction(gain_file, gpu_id)
            
    def create_stacks(self):
        print('------------- creating stacks ----------------')
        self.project_stacks.mkdir(exist_ok=True)
        for ts in self.tilt_series:
            ts.to_stacks(self.project_stacks, self.pixel_size)
            
    def aretomo(self, tilt_axis, vol_z, align_z, binning, tiltcor, tiltcor_angle, gpu_id):
        self.project_tomograms.mkdir(exist_ok=True)
        self.tomos_full.mkdir(exist_ok=True)
        self.tomos_odd.mkdir(exist_ok=True)
        self.tomos_even.mkdir(exist_ok=True)
        for ts in self.tilt_series:
            ts.reconstruction(self.tomos_full, self.tomos_even, self.tomos_odd, tilt_axis, 
                              vol_z, align_z, binning, tiltcor, tiltcor_angle, gpu_id)
            
    def cryocare(self, training_subset_size, cryocare_model_name, gpu_id):
        self.cryocare_folder.mkdir(exist_ok=True)
        self.tomos_denoised.mkdir(exist_ok=True)
        
        # move all XZ projections from AreTomo, otherwise cryocare tries to predict on them
        even_proj = self.tomos_even.joinpath('proj')
        odd_proj = self.tomos_odd.joinpath('proj')
        even_proj.mkdir(exist_ok=True)
        odd_proj.mkdir(exist_ok=True)
        subprocess.run(f'mv {str(self.tomos_even)}/*projX* {str(even_proj)}', shell=True)
        subprocess.run(f'mv {str(self.tomos_odd)}/*projX* {str(odd_proj)}', shell=True)
 
        train_data_file = self.project_main.joinpath('train_data_config.json')
        train_file = self.project_main.joinpath('train_config.json')
        predict_file = self.project_main.joinpath('predict_config.json')
        
        # select subset size indices
        subset = np.random.choice(len(self.tilt_series), training_subset_size)
        cryocare_train_data_config['path'] = str(self.cryocare_folder)
        cryocare_train_data_config['even'] = [str(self.tilt_series[i].tomo_even) for i in subset]
        cryocare_train_data_config['odd'] = [str(self.tilt_series[i].tomo_odd) for i in subset]
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
        
            
    def run(self, gain_file, tilt_axis, vol_z, align_z, binning, tiltcor, tiltcor_angle, 
            training_subset_size, cryocare_model_name, gpu_id):
        # run motioncor2
        self.motioncor2(gain_file, gpu_id)
        
        # combine to stacks
        self.create_stacks()        
        
        # run aretomo
        self.aretomo(tilt_axis, vol_z, align_z, binning, tiltcor, tiltcor_angle, gpu_id)        
        
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
                        help='gain file that is given to MotionCor2 for')
    parser.add_argument('--pixel-size', type=float, required=True,
                        help='specify the pixel size so mrcs can be annotated correctly')
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
    
    project = Project(project_path, args.pixel_size)
    project.run(gain_file, args.tilt_axis, args.aretomo_vol_z, args.aretomo_align_z,
                args.tomogram_binning, args.aretomo_tiltcor, args.aretomo_tiltcor_angle,
                args.training_size, args.cryocare_model_name, args.gpu_id)
	
