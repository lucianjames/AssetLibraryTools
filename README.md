# AssetLibraryTools

AssetLibraryTools is a free addon which aims to speed up the process of creating asset libraries with the asset browser, This addon is currently very much experimental as is the asset browser in blender.

# Features
* Batch import PBR materials from texture sets
  * Add real displacement to materials upon import
  * Add fake user to materials upon import
* Batch import models of various filetypes (fbx, gltf, obj, x3d)
  * Hide imported models straight after import
* Batch download CC0 assets from ambientcg.com via a python script
  * Filter assets by: Keyword, Resolution + filetype (For textures), File extension
  * Unzip downloaded zip files automatically
  * Delete zip files after unzip automatically
  * Skip downloading files that already exist
* Batch mark/unmark materials, meshes and objects as assets
* Delete all materials
* Delete all objects
* Delete all textures
* Delete all images
* Enable real displacement for cycles on all materials
* And more to come

![image](https://user-images.githubusercontent.com/65134690/126872960-f9bb5b44-0c0b-40f4-aa58-e77b2a8b24df.png)


# Plans for the future
(Some of these are more likely to happen than others)
* Fix known issues
* Extra options to customise the shader setup for batch material import
  * Multiple pre-sets such as “basic PBR setup”, “complex PBR setup” (for example)
* Multiple websites in asset downloading script
* GitHub wiki
* Quick YouTube tutorial
