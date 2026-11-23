[![Twitter: @NorowaretaGemu](https://img.shields.io/badge/X-@NorowaretaGemu-blue.svg?style=flat)](https://x.com/NorowaretaGemu)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](COPYING)

<br>
<div align="center">
  <a href="https://ko-fi.com/cursedentertainment">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="ko-fi" style="width: 20%;"/>
  </a>
</div>
<br>

<div align="center">
  <img alt="C++" src="https://img.shields.io/badge/C%2B%2B-%23323330.svg?&style=for-the-badge&logo=c%2B%2B&logoColor=white"/>
  <img alt="C" src="https://img.shields.io/badge/C-%23323330.svg?&style=for-the-badge&logo=c&logoColor=white"/>
  <img alt="Python" src="https://img.shields.io/badge/Python-%23323330.svg?&style=for-the-badge&logo=python&logoColor=white"/>
</div>
<br>

# Prometheus

**Shape people from clay.** Prometheus is Atelier's 3D suite: modelling, sculpting, animation, rendering and
compositing in one app, with three character creators built in. Built on Blender 5.4, it is part of
[Atelier](https://github.com/CursedPrograms/Atelier), Cursed Entertainment's creative suite, in Atelier's look.

**Website:** https://cursedprograms.github.io/Prometheus/

## What it is

Everything Blender 5.4 provides, under Prometheus's name and colours, plus a **Humans** tab in the 3D Viewport's
sidebar (N):

- **MB-Lab:** realistic men and women from sliders: body, face, age, mass and tone, measurements, expressions, a
  face rig, skin and eye materials, and proxy fitting for clothes.
- **CharMorph:** faster morphing on four bases (MB-Lab female and male, Antonia, Reom), direct skin and eye colours,
  hairstyles, real-time fitting of clothes and a Rigify rig with a full face rig. Its **Human Editor** tab makes new
  characters for it.
- **SMPL-X bodies:** the body model used in AI and motion capture research, with shape and expression sliders, a
  skeleton fitted to the shape and random shapes. SMPL and SMPL-H load too.
  The SMPL-X models are free for **non-commercial use only**, so they aren't included: register at
  [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de), download the `.npz` models and set their folder in
  Preferences > Add-ons > SMPL-X Bodies.

Files, add-ons and tutorials made for Blender 5.4 work in Prometheus as they are.

### What Prometheus changes

- The name in the title bar and the About box (with Blender's credits kept).
- Its own settings folder, `%APPDATA%\Cursed Entertainment\Prometheus` (`~/.config/prometheus` on Linux), so it
  never touches a Blender install's settings.
- The default theme: the Atelier blue `#007bb7`, square corners, no shadows.
- MB-Lab, CharMorph and SMPL-X Bodies built in and switched on, with their self-updaters removed (they update with
  Prometheus).

## Minimum requirements

| | |
| --- | --- |
| **System** | Windows 10 or 11, 64-bit (Linux builds from source) |
| **Processor** | 64-bit, 4 cores, with SSE4.2 |
| **Memory** | 8 GB RAM (16 GB for big scenes and 8K skin textures) |
| **Graphics** | a card with OpenGL 4.3 or Vulkan 1.2 and 2 GB of video memory |
| **Disk** | 3 GB, plus your projects |

## Build

Needs Visual Studio 2022 (C++), CMake, Git with Git LFS, and Python 3.

```bat
git config lfs.fetchexclude "tests/**"    :: skip Blender's test files (several GB the build doesn't need)
python build_files\utils\make_update.py   :: first time: Blender's prebuilt Windows libraries and data files
make.bat release                          :: builds Prometheus
```

## Credits

Based on [Blender](https://www.blender.org) (GPL-3), © Blender Foundation and Blender contributors. See
[COPYING](COPYING) and [blender.org/about/license](https://www.blender.org/about/license).

- **MB-Lab**, © 2015-2018 Manuel Bastioni and the MB-Lab community: code GPL-3, data AGPL-3.
- **CharMorph**, © 2020-2021 Michael Vigovsky: code GPL-3; each of its characters carries its own licence.
- **Antonia** (CharMorph): Olaf Delgado-Friedrichs; morphs by phantom3D, MikeJ, DieTrying, Fenrissa and others. CC-BY 3.0.
- **Reom** (CharMorph): mesh by ComplexAce, morphs and textures by Hope. CC-BY.
- **PyYAML** (bundled with CharMorph): © Ingy döt Net, Kirill Simonov. MIT.
- **SMPL-X** (not included): Max Planck Institute for Intelligent Systems, under its own licence.

<br>

---
<br>
<div align="center">
<a href="https://github.com/Farica-Kimora">Farica☆Kimora</a> © Cursed Entertainment 2026
</div>
<br>
<div align="center">
<a href="https://cursed-entertainment.itch.io/" target="_blank">
    <img src="https://github.com/CursedPrograms/cursedentertainment/raw/main/images/logos/logo-wide-grey.png"
        alt="CursedEntertainment Logo" style="width:250px;">
</a>
</div>
