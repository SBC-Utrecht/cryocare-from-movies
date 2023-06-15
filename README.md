# cryocare-from-movies
Automatically processes data from a folder with raw tifs and mdocs to cryocare denoised tomograms.

# HOW TO RUN?

```module load motioncor2 aretomo miniconda/cryocare```

```condaactivate```

Run this script in the following folder structure:

```
project/
+- raw/
Â¦  +- tomo200528_100.mrc.mdoc
Â¦  +- tomo200528_100_0.0_May30_22.19.28.tif
Â¦  +- tomo200528_100_3.0_May30_22.20.54.tif
Â¦  +- ...
Â¦  +- tomo200528_110.mrc.mdoc
Â¦  +- tomo200528_110_0.0_May30_22.19.28.tif
Â¦  +- tomo200528_110_3.0_May30_22.20.54.tif
Â¦  +- etc...

This script will modify it with the following output:

project/
+- raw/
Â¦  +- tomo200528_100.mrc.mdoc
Â¦  +- tomo200528_100_0.0_May30_22.19.28.tif
Â¦  +- tomo200528_100_3.0_May30_22.20.54.tif
Â¦  +- ...
Â¦  +- tomo200528_110.mrc.mdoc
Â¦  +- tomo200528_110_0.0_May30_22.19.28.tif
Â¦  +- tomo200528_110_3.0_May30_22.20.54.tif
Â¦  +- etc...
+- stacks/
Â¦  +- tomo200528_100.st
Â¦  +- tomo200528_100_odd.st
Â¦  +- tomo200528_100_even.st
Â¦  +- tomo200528_100.rawtlt
Â¦  +- tomo200528_110.st
Â¦  +- tomo200528_110_odd.st
Â¦  +- tomo200528_110_even.st
Â¦  +- tomo200528_110.rawtlt
+- tomograms/
Â¦  +- full/
Â¦  Â¦  +- tomo200528_100.mrc
Â¦  Â¦  +- tomo200528_100.aln
Â¦  Â¦  +- tomo200528_110.mrc
Â¦  Â¦  +- tomo200528_110.aln
Â¦  +- even/
Â¦  Â¦  +- tomo200528_100.mrc
Â¦  Â¦  +- tomo200528_110.mrc
Â¦  +- odd/
Â¦  Â¦  +- tomo200528_100.mrc
Â¦  Â¦  +- tomo200528_110.mrc
Â¦  +- denoised/
Â¦  Â¦  +- tomo200528_100.mrc
Â¦  Â¦  +- tomo200528_110.mrc
Â¦  +- cryocare_model/
```
