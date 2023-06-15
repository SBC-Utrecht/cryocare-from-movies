# cryocare-from-movies
Automatically processes data from a folder with raw tifs and mdocs to cryocare denoised tomograms.

# HOW TO RUN?

```module load motioncor2 aretomo miniconda/cryocare```

```condaactivate```

Run this script in the following folder structure:

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

(or make the script executable)

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
