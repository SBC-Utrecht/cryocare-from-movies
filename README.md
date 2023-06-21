# cryocare-from-movies
Automatically processes data from a folder with raw tifs and mdocs to cryocare denoised tomograms.

# HOW TO RUN?

```module load motioncor2 aretomo miniconda/cryocare```

```condaactivate```

To run (altenatively can make the script executable):

```python path/to/script/tomo_prepper.py --help```

Some info about parameters:
- MotionCor2 will correct motion without local patches, its just a single xy translation per frame.
- Some of the script options directly refer to aretomo parameters, check their docs for usage instructions!
- cryocare relies on a parameter 'training-size' that randomly selects n tomograms to train the denoiser on. I have no idea what an appropriate setting is (even made a github issue in their repo about it: https://github.com/juglab/cryoCARE_pip/issues/50). I used a small subset of my tilt-series for training but someone else trained it on 100 tomograms with much longer training times. I had succes with 5 tomograms and running times were very feasible.
- You need to provide a single GPU.

Run this script in the following folder structure, where the project folder can have an arbitrary name but the folder 'raw' is hardcoded:

```
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
```

```python path/to/script/tomo_prepper.py --project-dir path/to/project```

This script will modify it with the following output:

```
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
```
