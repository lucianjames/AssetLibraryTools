bl_info = {
    "name": "AssetLibraryTools",
    "description": "AssetLibraryTools is a free addon which aims to speed up the process of creating asset libraries with the asset browser, This addon is currently very much experimental as is the asset browser in blender.",
    "author": "Lucian James (LJ3D)",
    "version": (0, 2, 0),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
    "warning": "Developed in 3.0 ALPHA. May be unstable or broken in future versions", # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/LJ3D/AssetLibraryTools/wiki",
    "tracker_url": "https://github.com/LJ3D/AssetLibraryTools",
    "category": "3D View"
}

import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       )
import pathlib
import re
import os
import time
import random


# ------------------------------------------------------------------------
#    Stuff
# ------------------------------------------------------------------------ 

diffNames = ["diffuse", "diff", "albedo", "base", "col", "color"]
sssNames = ["sss", "subsurface"]
metNames = ["metallic", "metalness", "metal", "mtl", "met"]
specNames = ["specularity", "specular", "spec", "spc"]
roughNames = ["roughness", "rough", "rgh", "gloss", "glossy", "glossiness"]
normNames = ["normal", "nor", "nrm", "nrml", "norm"]
dispNames = ["displacement", "displace", "disp", "dsp", "height", "heightmap", "bump", "bmp"]
alphaNames = ["alpha", "opacity"]
emissiveNames = ["emissive", "emission"]

nameLists = [diffNames, sssNames, metNames, specNames, roughNames, normNames, dispNames, alphaNames, emissiveNames]
texTypes = ["diff", "sss", "met", "spec", "rough", "norm", "disp", "alpha", "emission"]

# Find the type of PBR texture a file is based on its name
def FindPBRTextureType(fname):
    PBRTT = None
    # Remove digits
    fname = ''.join(i for i in fname if not i.isdigit())
    # Separate CamelCase by space
    fname = re.sub("([a-z])([A-Z])","\g<1> \g<2>",fname)
    # Replace common separators with SPACE
    seperators = ['_', '.', '-', '__', '--', '#']
    for sep in seperators:
        fname = fname.replace(sep, ' ')
    # Set entire string to lower case
    fname = fname.lower()
    # Find PBRTT
    i = 0
    for nameList in nameLists:
        for name in nameList:
            if name in fname:
                PBRTT = texTypes[i]
        i+=1
    return PBRTT


# Display a message in the blender UI
def DisplayMessageBox(message = "", title = "Info", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


# Class with functions for setting up shaders
class shaderSetup():
    
    def createNode(mat, type, name="newNode", location=(0,0)):
        nodes = mat.node_tree.nodes
        n = nodes.new(type=type)
        n.name = name
        n.location = location
        return n
    
    def setMapping(node):
        tool = bpy.context.scene.assetlibrarytools
        if tool.texture_mapping == 'Object':
                node.projection = 'BOX'
                node.projection_blend = 1
    
    def simplePrincipledSetup(name, files):
        tool = bpy.context.scene.assetlibrarytools
        # Create a new empty material
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links 
        nodes.clear() # Delete all nodes
        
        # Load textures
        diffuseTexture = None
        sssTexture = None
        metallicTexture = None
        specularTexture = None
        roughnessTexture = None
        emissionTexture = None
        alphaTexture = None
        normalTexture = None
        displacementTexture = None
        for i in files:
            t = FindPBRTextureType(i.name)
            if t == "diff":
                diffuseTexture = bpy.data.images.load(str(i))
            elif t == "sss":
                sssTexture = bpy.data.images.load(str(i))
                sssTexture.colorspace_settings.name = 'Non-Color'
            elif t == "met":
                metallicTexture = bpy.data.images.load(str(i))
                metallicTexture.colorspace_settings.name = 'Non-Color'
            elif t == "spec":
                specularTexture = bpy.data.images.load(str(i))
                specularTexture.colorspace_settings.name = 'Non-Color'
            elif t == "rough":
                roughnessTexture = bpy.data.images.load(str(i))
                roughnessTexture.colorspace_settings.name = 'Non-Color'
            elif t == "emission":
                emissionTexture = bpy.data.images.load(str(i))  
            elif t == "alpha":
                alphaTexture = bpy.data.images.load(str(i))
                alphaTexture.colorspace_settings.name = 'Non-Color'
            elif t == "norm":
                normalTexture = bpy.data.images.load(str(i))
                normalTexture.colorspace_settings.name = 'Non-Color'
            elif t == "disp":
                displacementTexture = bpy.data.images.load(str(i))
                displacementTexture.colorspace_settings.name = 'Non-Color'
        
        # Create base nodes
        node_output = shaderSetup.createNode(mat, "ShaderNodeOutputMaterial", "node_output", (250,0))
        node_principled = shaderSetup.createNode(mat, "ShaderNodeBsdfPrincipled", "node_principled", (-300,0))
        node_mapping = shaderSetup.createNode(mat, "ShaderNodeMapping", "node_mapping", (-1300,0))
        node_texCoord = shaderSetup.createNode(mat, "ShaderNodeTexCoord", "node_texCoord", (-1500,0))
        # Link base nodes
        links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
        links.new(node_texCoord.outputs[tool.texture_mapping], node_mapping.inputs['Vector'])
        
        # Create, fill, and link texture nodes
        imported_tex_nodes = 0
        if diffuseTexture != None and tool.import_diff != False:
            node_imTexDiffuse = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexDiffuse", (-800,300-(300*imported_tex_nodes)))
            node_imTexDiffuse.image = diffuseTexture
            links.new(node_imTexDiffuse.outputs['Color'], node_principled.inputs['Base Color'])
            links.new(node_mapping.outputs['Vector'], node_imTexDiffuse.inputs['Vector'])
            shaderSetup.setMapping(node_imTexDiffuse)
            imported_tex_nodes += 1
            
        if sssTexture != None and tool.import_sss != False:
            node_imTexSSS = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexSSS", (-800,300-(300*imported_tex_nodes)))
            node_imTexSSS.image = sssTexture
            links.new(node_imTexSSS.outputs['Color'], node_principled.inputs['Subsurface'])
            links.new(node_mapping.outputs['Vector'], node_imTexSSS.inputs['Vector'])
            shaderSetup.setMapping(node_imTexSSS)
            imported_tex_nodes += 1
            
        if metallicTexture != None and tool.import_met != False:
            node_imTexMetallic = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexMetallic", (-800,300-(300*imported_tex_nodes)))
            node_imTexMetallic.image = metallicTexture
            links.new(node_imTexMetallic.outputs['Color'], node_principled.inputs['Metallic'])
            links.new(node_mapping.outputs['Vector'], node_imTexMetallic.inputs['Vector'])
            shaderSetup.setMapping(node_imTexMetallic)
            imported_tex_nodes += 1
            
        if specularTexture != None and tool.import_spec != False:
            node_imTexSpecular = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexSpecular", (-800,300-(300*imported_tex_nodes)))
            node_imTexSpecular.image = specularTexture
            links.new(node_imTexSpecular.outputs['Color'], node_principled.inputs['Specular'])
            links.new(node_mapping.outputs['Vector'], node_imTexSpecular.inputs['Vector'])
            shaderSetup.setMapping(node_imTexSpecular)
            imported_tex_nodes += 1
            
        if roughnessTexture != None and tool.import_rough != False:
            node_imTexRoughness = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexRoughness", (-800,300-(300*imported_tex_nodes)))
            node_imTexRoughness.image = roughnessTexture
            links.new(node_imTexRoughness.outputs['Color'], node_principled.inputs['Roughness'])
            links.new(node_mapping.outputs['Vector'], node_imTexRoughness.inputs['Vector'])
            shaderSetup.setMapping(node_imTexRoughness)
            imported_tex_nodes += 1
            
        if emissionTexture != None and tool.import_emission != False:
            node_imTexEmission = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexEmission", (-800,300-(300*imported_tex_nodes)))
            node_imTexEmission.image = emissionTexture
            links.new(node_imTexEmission.outputs['Color'], node_principled.inputs['Emission'])
            links.new(node_mapping.outputs['Vector'], node_imTexEmission.inputs['Vector'])
            shaderSetup.setMapping(node_imTexEmission)
            imported_tex_nodes += 1
            
        if alphaTexture != None and tool.import_alpha != False:
            node_imTexAlpha = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexAlpha", (-800,300-(300*imported_tex_nodes)))
            node_imTexAlpha.image = alphaTexture
            links.new(node_imTexAlpha.outputs['Color'], node_principled.inputs['Alpha'])
            links.new(node_mapping.outputs['Vector'], node_imTexAlpha.inputs['Vector'])
            shaderSetup.setMapping(node_imTexAlpha)
            imported_tex_nodes += 1
            
        if normalTexture != None and tool.import_norm != False:
            node_imTexNormal = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexNormal", (-800,300-(300*imported_tex_nodes)))
            node_imTexNormal.image = normalTexture
            node_normalMap = shaderSetup.createNode(mat, "ShaderNodeNormalMap", "node_normalMap", (-500,300-(300*imported_tex_nodes)))
            links.new(node_imTexNormal.outputs['Color'], node_normalMap.inputs['Color'])
            links.new(node_normalMap.outputs['Normal'], node_principled.inputs['Normal'])
            links.new(node_mapping.outputs['Vector'], node_imTexNormal.inputs['Vector'])
            shaderSetup.setMapping(node_imTexNormal)
            imported_tex_nodes += 1
            
        if displacementTexture != None and tool.import_disp != False:
            node_imTexDisplacement = shaderSetup.createNode(mat, "ShaderNodeTexImage", "node_imTexDisplacement", (-800,300-(300*imported_tex_nodes)))
            node_imTexDisplacement.image = displacementTexture
            node_displacement = shaderSetup.createNode(mat, "ShaderNodeDisplacement", "node_displacement", (-200,-600))
            links.new(node_imTexDisplacement.outputs['Color'], node_displacement.inputs['Height'])
            links.new(node_displacement.outputs['Displacement'], node_output.inputs['Displacement'])
            links.new(node_mapping.outputs['Vector'], node_imTexDisplacement.inputs['Vector'])
            shaderSetup.setMapping(node_imTexDisplacement)
            imported_tex_nodes += 1
        
        return mat


def listDownloadAttribs(scene, context):
    scene = context.scene
    tool = scene.assetlibrarytools
    if tool.showAllDownloadAttribs == True:
        attribs = ['None', '1K-JPG', '1K-PNG', '2K-JPG', '2K-PNG', '4K-JPG', '4K-PNG', '8K-JPG', '8K-PNG', '12K-HDR', '16K-HDR', '1K-HDR', '2K-HDR', '4K-HDR', '8K-HDR', '12K-TONEMAPPED', '16K-TONEMAPPED', '1K-TONEMAPPED', '2K-TONEMAPPED', '4K-TONEMAPPED', '8K-TONEMAPPED', '12K-JPG', '12K-PNG', '16K-JPG', '16K-PNG', '1K-HQ-JPG', '1K-HQ-PNG', '1K-LQ-JPG', '1K-LQ-PNG', '1K-SQ-JPG', '1K-SQ-PNG', '2K-HQ-JPG', '2K-HQ-PNG', '2K-LQ-JPG', '2K-LQ-PNG', '2K-SQ-JPG', '2K-SQ-PNG', '4K-HQ-JPG', '4K-HQ-PNG', '4K-LQ-JPG', '4K-LQ-PNG', '4K-SQ-JPG', '4K-SQ-PNG', 'HQ', 'LQ', 'SQ', '24K-JPG', '24K-PNG', '32K-JPG', '32K-PNG', '6K-JPG', '6K-PNG', '2K', '4K', '8K', '1K', 'CustomImages', '16K', '9K', '1000K', '250K', '25K', '5K-JPG', '5K-PNG', '2kPNG', '4kPNG', '2kPNG-PNG', '4kPNG-PNG', '9K-JPG', '10K-JPG', '7K-JPG', '7K-PNG', '3K-JPG', '3K-PNG', '9K-PNG', '33K-JPG', '33K-PNG', '15K-JPG', '15K-PNG']
    else:
        attribs = ['None', '1K-JPG', '1K-PNG', '2K-JPG', '2K-PNG', '4K-JPG', '4K-PNG', '8K-JPG', '8K-PNG']
    items = []
    for a in attribs:
        items.append((a, a, ""))
    return items


# ------------------------------------------------------------------------
#    Properties
# ------------------------------------------------------------------------ 

class properties(PropertyGroup):
    
    # Material import properties
    mat_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import PBR texture sets from.\nFormat your files like this: ChosenDirectory/PBRTextureName/textureFiles",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    skip_existing : BoolProperty(
        name = "Skip existing",
        description = "Dont import materials if a material with the same name already exists",
        default = True
        )
    use_fake_user : BoolProperty(
        name = "Use fake user",
        description = "Use fake user on imported materials",
        default = True
        )
    use_real_displacement : BoolProperty(
        name = "Use real displacement",
        description = "Enable real geometry displacement in the material settings (cycles only)",
        default = False
        )
    texture_mapping : EnumProperty(
        name='Mapping',
        default='UV',
        items=[('UV', 'UV', 'Use UVs to control mapping'),
        ('Object', 'Object', 'Wrap texture along world coords')])
    import_diff : BoolProperty(
        name = "Import diffuse",
        description = "",
        default = True
        )
    import_sss : BoolProperty(
        name = "Import SSS",
        description = "",
        default = True
        )
    import_met : BoolProperty(
        name = "Import metallic",
        description = "",
        default = True
        )
    import_spec : BoolProperty(
        name = "Import specularity",
        description = "",
        default = True
        )   
    import_rough : BoolProperty(
        name = "Import roughness",
        description = "",
        default = True
        )
    import_emission : BoolProperty(
        name = "Import emission",
        description = "",
        default = True
        )
    import_alpha : BoolProperty(
        name = "Import alpha",
        description = "",
        default = True
        )
    import_norm : BoolProperty(
        name = "Import normal",
        description = "",
        default = True
        )
    import_disp : BoolProperty(
        name = "Import displacement",
        description = "",
        default = True
        )
    
    
    # Model import properties
    model_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import models from.\nSubdirectories are checked recursively",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    hide_after_import : BoolProperty(
        name = "Hide models after import",
        description = "Reduces viewport polycount, prevents low framerate/crashes.\nHides each model individually straight after import",
        default = False
        )
    import_fbx : BoolProperty(
        name = "Import FBX files",
        description = "",
        default = True
        )
    import_gltf : BoolProperty(
        name = "Import GLTF files",
        description = "",
        default = True
        )
    import_obj : BoolProperty(
        name = "Import OBJ files",
        description = "",
        default = True
        )
    import_x3d : BoolProperty(
        name = "Import X3D files",
        description = "",
        default = True
        )
        
        
    # Batch append properties
    append_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch append from.",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    append_recursive_search : BoolProperty(
        name = "Search for .blend files in surbdirs recursively",
        description = "",
        default = False
        )
    appendType : EnumProperty(
        name="Append",
        description="Choose type to append",
        items=[ ('objects', "Objects", ""),
                ('materials', "Materials", ""),
                ]
        )
    deleteLights : BoolProperty(
        name = "Dont append lights",
        description = "",
        default = True
        )
    deleteCameras : BoolProperty(
        name = "Dont append cameras",
        description = "",
        default = True
        )
    
    
    # Asset management properties
    markunmark : EnumProperty(
        name="Operation",
        description="Choose whether to mark assets, or unmark assets",
        items=[ ('mark', "Mark assets", ""),
                ('unmark', "Unmark assets", ""),
               ]
        )
    assettype : EnumProperty(
        name="On type",
        description="Choose a type of asset to mark/unmark",
        items=[ ('objects', "Objects", ""),
                ('materials', "Materials", ""),
                ('images', "Images", ""),
                ('textures', "Textures", ""),
                ('meshes', "Meshes", ""),
               ]
        )
    previewgentype : EnumProperty(
        name="Asset type",
        description="Choose a type of asset to mark/unmark",
        items=[ ('objects', "Objects", ""),
                ('materials', "Materials", ""),
                ('images', "Images", ""),
                ('textures', "Textures", ""),
                ('meshes', "Meshes", ""),
               ]
        )
    
    
    # Utilities panel properties
    deleteType : EnumProperty(
        name="Delete all",
        description="Choose type to batch delete",
        items=[ ('objects', "Objects", ""),
                ('materials', "Materials", ""),
                ('images', "Images", ""),
                ('textures', "Textures", ""),
                ('meshes', "Meshes", ""),
               ]
        )
    dispNewScale: FloatProperty(
        name = "New Displacement Scale",
        description = "A float property",
        default = 0.1,
        min = 0.0001
        )
    
    
    # Asset snapshot panel properties
    resolution : IntProperty(
            name="Preview Resolution",
            description="Resolution to render the preview",
            min=1,
            soft_max=500,
            default=256
            )
    
    
    # CC0AssetDownloader properties
    downloader_save_path : StringProperty(
        name = "Save location",
        description = "Choose a directory to save assets to",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    keywordFilter : StringProperty(
        name = "Keyword filter",
        description = "Enter a keyword to filter assets by, leave empty if you do not wish to filter.",
        default = "",
        maxlen = 1024,
        )
    showAllDownloadAttribs: BoolProperty(
        name = "Show all download attributes",
        description = "",
        default = True
        )
    attributeFilter : EnumProperty(
        name="Attribute filter",
        description="Choose attribute to filter assets by",
        items=listDownloadAttribs
        )
    extensionFilter : EnumProperty(
        name="Extension filter",
        description="Choose file extension to filter assets by",
        items=[ ('None', "None", ""),
                ('zip', "ZIP", ""),
                ('obj', "OBJ", ""),
                ('exr', "EXR", ""),
                ('sbsar', "SBSAR", ""),
               ]
        )
    unZip : BoolProperty(
        name = "Unzip downloaded zip files",
        description = "",
        default = True
        )
    deleteZips : BoolProperty(
        name = "Delete zip files after they have been unzipped",
        description = "",
        default = True
        )
    skipDuplicates : BoolProperty(
        name = "Dont download files which already exist",
        description = "",
        default = True
        )
    terminal : EnumProperty(
        name="Terminal",
        description="Choose terminal to run script with",
        items=[ ('cmd', "cmd", ""),
                ('gnome-terminal', "gnome-terminal", ""),
                ('konsole', 'konsole', ""),
                ('xterm', 'xterm', ""),
               ]
        )
    
    
    # SBSAR import properties
    sbsar_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import sbsar files from.\nSubdirectories are checked recursively",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    
    
    # UI properties
    matImport_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    matImportOptions_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    append_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    modelImport_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    modelImportOptions_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    assetBrowserOpsRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    utilRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    snapshotRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    assetDownloaderRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    sbsarImport_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )

# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class OT_BatchImportPBR(Operator):
    bl_label = "Import PBR textures"
    bl_idname = "alt.batchimportpbr"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        n_imp = 0 # Number of materials imported
        n_del = 0 # Number of materials deleted (due to no textures after import)
        n_skp = 0 # Number of materials skipped due to them already existing
        existing_mat_names = []
        subdirectories = [x for x in pathlib.Path(tool.mat_import_path).iterdir() if x.is_dir()] # Get subdirs in directory selected in UI
        for sd in subdirectories:
            filePaths = [x for x in pathlib.Path(sd).iterdir() if x.is_file()] # Get filepaths of textures
            # Get existing material names if skipping existing materials is turned on
            if tool.skip_existing == True:
                existing_mat_names = []
                for mat in bpy.data.materials:
                    existing_mat_names.append(mat.name)
            # check if the material thats about to be imported exists or not, or if we dont care about skipping existing materials.
            if (sd.name not in existing_mat_names) or (tool.skip_existing != True):
                mat = shaderSetup.simplePrincipledSetup(sd.name, filePaths) # Create shader using filepaths of textures
                if tool.use_fake_user == True: # Enable fake user (if desired)
                    mat.use_fake_user = True
                if tool.use_real_displacement == True: # Enable real displacement (if desired)
                    mat.cycles.displacement_method = 'BOTH'
                # Delete the material if it contains no textures
                hasTex = False
                for n in mat.node_tree.nodes: 
                    if n.type == 'TEX_IMAGE': # Check if shader contains textures, if yes, then its worth keeping
                        hasTex = True
                if hasTex == False:
                    bpy.data.materials.remove(mat) # Delete material if it contains no textures
                    n_del += 1
                else:
                    n_imp += 1
            else:
                n_skp += 1
        if (n_del > 0) and (n_skp > 0):
            DisplayMessageBox("Complete, {0} materials imported, {1} were deleted after import because they contained no textures (No recognised textures were found in the folder), {2} skipped because they already exist".format(n_imp,n_del,n_skp))
        elif n_skp > 0:
            DisplayMessageBox("Complete, {0} materials imported. {1} skipped because they already exist".format(n_imp, n_skp))
        elif n_del > 0:
            DisplayMessageBox("Complete, {0} materials imported, {1} were deleted after import because they contained no textures (No recognised textures were found in the folder)".format(n_imp,n_del))
        else:
            DisplayMessageBox("Complete, {0} materials imported".format(n_imp))
        return{'FINISHED'}


class OT_ImportModels(Operator):
    bl_label = "Import models"
    bl_idname = "alt.importmodels"
    
    # Hide new objects works by comparing a list of objects before (x) happened with the current list via bpy.context.scene.objects to get the list of new objects, then hides those new objects
    def hideNewObjects(old_objects):
        scene = bpy.context.scene
        tool = scene.assetlibrarytools
        imported_objects = set(bpy.context.scene.objects) - old_objects
        if tool.hide_after_import == True:
            for object in imported_objects:
                object.hide_set(True)
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        p = pathlib.Path(str(tool.model_import_path))
        imported = 0 # Number of imported objects
        errors = 0 # Number of import errors
        # Import FBX files
        if tool.import_fbx == True:
            fbxFilePaths = [x for x in p.glob('**/*.fbx') if x.is_file()] # Get filepaths of files with the extension .fbx in the selected directory (and subdirs, recursively)
            for filePath in fbxFilePaths:
                old_objects = set(context.scene.objects)
                try:
                    bpy.ops.import_scene.fbx(filepath=str(filePath))
                    imported += 1
                except:
                    print("FBX import error")
                    errors += 1
        # Import GLTF files
        if tool.import_gltf == True:
            gltfFilePaths = [x for x in p.glob('**/*.gltf') if x.is_file()] # Get filepaths of files with the extension .gltf in the selected directory (and subdirs, recursively)
            for filePath in gltfFilePaths:
                old_objects = set(context.scene.objects)
                try:
                    bpy.ops.import_scene.gltf(filepath=str(filePath))
                    imported += 1
                except:
                    print("GLTF import error")
                    errors += 1
                OT_ImportModels.hideNewObjects(old_objects)
        # Import OBJ files
        if tool.import_obj == True:
            objFilePaths = [x for x in p.glob('**/*.obj') if x.is_file()] # Get filepaths of files with the extension .obj in the selected directory (and subdirs, recursively)
            for filePath in objFilePaths:
                old_objects = set(context.scene.objects)
                try:
                    bpy.ops.import_scene.obj(filepath=str(filePath))
                    imported += 1
                except:
                    print("OBJ import error")
                    errors += 1
                OT_ImportModels.hideNewObjects(old_objects)
        # Import X3D files
        if tool.import_x3d == True:
            x3dFilePaths = [x for x in p.glob('**/*.x3d') if x.is_file()] # Get filepaths of files with the extension .x3d in the selected directory (and subdirs, recursively)
            for filePath in x3dFilePaths:
                old_objects = set(context.scene.objects)
                try:
                    bpy.ops.import_scene.x3d(filepath=str(filePath))
                    imported += 1
                except:
                    print("X3D import error")
                    errors += 1
                OT_ImportModels.hideNewObjects(old_objects)
        if errors == 0:
            DisplayMessageBox("Complete, {0} models imported".format(imported))
        else:
            DisplayMessageBox("Complete, {0} models imported. {1} import errors".format(imported, errors))
        return{'FINISHED'}


class OT_BatchAppend(Operator):
    bl_label = "Append"
    bl_idname = "alt.batchappend"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        p = pathlib.Path(str(tool.append_path))
        link = False # append, set to true to keep the link to the original file
        if tool.append_recursive_search == True:
            blendFilePaths = [x for x in p.glob('**/*.blend') if x.is_file()] # Get filepaths of files with the extension .blend in the selected directory (and subdirs, recursively)
        else:
            blendFilePaths = [x for x in p.glob('*.blend') if x.is_file()] # Get filepaths of files with the extension .blend in the selected directory    
        for path in blendFilePaths:
            if tool.appendType == 'objects':
                # link all objects
                with bpy.data.libraries.load(str(path), link=link) as (data_from, data_to):
                    data_to.objects = data_from.objects
                #link object to current scene
                for obj in data_to.objects:
                    removed = False
                    if obj is not None:
                       #bpy.context.scene.objects.link(obj) # Blender 2.7x
                       bpy.context.collection.objects.link(obj) # Blender 2.8x   
                    # remove cameras
                    if removed == False and tool.deleteCameras == True: # This stops an error from occuring if obj is already deleted
                        if obj.type == 'CAMERA':
                            bpy.data.objects.remove(obj)
                            removed = True      
                    # remove lights
                    if removed == False and tool.deleteLights == True: # This stops an error from occuring if obj is already deleted
                        if obj.type == 'LIGHT':
                            bpy.data.objects.remove(obj)
                            removed = True
            if tool.appendType == 'materials':
                with bpy.data.libraries.load(str(path), link=link) as (data_from, data_to):
                    data_to.materials = data_from.materials
        if tool.appendType == 'objects':
             DisplayMessageBox("Complete, objects appended")
        if tool.appendType == 'materials':
            DisplayMessageBox("Complete, materials appended")
        return{'FINISHED'}


class OT_ManageAssets(Operator):
    bl_label = "Go"
    bl_idname = "alt.manageassets"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        i = 0 # Number of assets modified
        # Mark assets
        if tool.markunmark == 'mark':
            if tool.assettype == 'objects':
                for object in bpy.data.objects:
                    object.asset_mark()
                    i += 1
            if tool.assettype == 'materials':
                for mat in bpy.data.materials:
                    mat.asset_mark()
                    i += 1
            if tool.assettype == 'images':
                for image in bpy.data.images:
                    image.asset_mark()
                    i += 1      
            if tool.assettype == 'textures':
                for texture in bpy.data.textures:
                    texture.asset_mark()
                    i += 1   
            if tool.assettype == 'meshes':
                for mesh in bpy.data.meshes:
                    mesh.asset_mark()
                    i += 1
            DisplayMessageBox("Complete, {0} assets marked".format(i))
        # Unmark assets
        if tool.markunmark == 'unmark':
            if tool.assettype == 'objects':
                for object in bpy.data.objects:
                    object.asset_clear()
                    i += 1
            if tool.assettype == 'materials':
                for mat in bpy.data.materials:
                    mat.asset_clear()
                    i += 1 
            if tool.assettype == 'images':
                for image in bpy.data.images:
                    image.asset_clear()
                    i += 1  
            if tool.assettype == 'textures':
                for texture in bpy.data.textures:
                    texture.asset_clear()
                    i += 1
            if tool.assettype == 'meshes':
                for mesh in bpy.data.meshes:
                    mesh.asset_clear()
                    i += 1
            DisplayMessageBox("Complete, {0} assets unmarked".format(i))
        return {'FINISHED'}


class OT_GenerateAssetPreviews(Operator):
    bl_label = "Generate previews"
    bl_idname = "alt.generateassetpreviews"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        if tool.previewgentype == 'objects':
            for obj in bpy.data.objects:
                if obj.asset_data:
                    obj.asset_generate_preview()
        if tool.previewgentype == 'materials':
            for mat in bpy.data.materials:
                if mat.asset_data:
                    mat.asset_generate_preview()
        if tool.previewgentype == 'images':
            for img in bpy.data.images:
                if img.asset_data:
                    img.asset_generate_preview()
        if tool.previewgentype == 'textures':
            for tex in bpy.data.textures:
                if tex.asset_data:
                    tex.asset_generate_preview()      
        if tool.previewgentype == 'meshes':
            for mesh in bpy.data.meshes:
                if mesh.asset_data:
                    mesh.asset_generate_preview()      
        return {'FINISHED'}


class OT_BatchDelete(Operator):
    bl_label = "Go"
    bl_idname = "alt.batchdelete"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        i = 0 # Number of items deleted
        if tool.deleteType == 'objects':
            for object in bpy.data.objects:
                bpy.data.objects.remove(object)
                i += 1
        if tool.deleteType == 'materials':
            for mat in bpy.data.materials:
                bpy.data.materials.remove(mat)
                i += 1
        if tool.deleteType == 'images':
            while len(bpy.data.images) > 0: # Cant use a for loop like the other "delete all" operations for some reason
                bpy.data.images.remove(bpy.data.images[0])
                i += 1
        if tool.deleteType == 'textures':
            for tex in bpy.data.textures:
                bpy.data.textures.remove(tex)
                i += 1    
        if tool.deleteType == 'meshes':
            for mesh in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
                i += 1
        DisplayMessageBox("Done, {0} {1} deleted".format(i, tool.deleteType))
        return {'FINISHED'}


class OT_SimpleDelDupeMaterials(Operator):
    bl_label = "Clean up duplicate materials (simple)"
    bl_idname = "alt.simpledeldupemats"
    def execute(self, context):
        for obj in bpy.data.objects:
            for slt in obj.material_slots:
                part = slt.name.rpartition('.')
                if part[2].isnumeric() and part[0] in bpy.data.materials:
                    slt.material = bpy.data.materials.get(part[0])
        DisplayMessageBox("Done")
        return {'FINISHED'}


class OT_CleanupUnusedMaterials(Operator):
    bl_label = "Clean up unused materials"
    bl_idname = "alt.cleanupunusedmats"
    def execute(self, context):
        i = 0
        for mat in bpy.data.materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)
                i += 1
        DisplayMessageBox("Done, {0} unused materials deleted".format(i))
        return {'FINISHED'}


class OT_UseDisplacementOnAll(Operator):
    bl_label = "Use real displacement on all materials"
    bl_idname = "alt.userealdispall"
    def execute(self, context):
        for mat in bpy.data.materials:
            mat.cycles.displacement_method = 'BOTH'
        DisplayMessageBox("Done")
        return {'FINISHED'}


class OT_ChangeAllDisplacementScale(Operator):
    bl_label = "Change displacement scale on all materials"
    bl_idname = "alt.changealldispscale"
    def execute(self, context):
        tool = context.scene.assetlibrarytools
        i = 0 # number of nodes changed
        for mat in bpy.data.materials:
            if mat is not None and mat.use_nodes and mat.node_tree is not None:
                for node in mat.node_tree.nodes:
                    if node.type == 'DISPLACEMENT':
                        node.inputs[2].default_value = tool.dispNewScale
                        i += 1
        DisplayMessageBox("Done, {0} nodes changed".format(i))
        return {'FINISHED'}


def snapshot(self,context,ob):
    scene = context.scene
    tool = scene.assetlibrarytools
    # Make sure we have a camera
    if bpy.context.scene.camera == None:
        bpy.ops.object.camera_add()
    
    #Save some basic settings
    camera = bpy.context.scene.camera    
    hold_camerapos = camera.location.copy()
    hold_camerarot = camera.rotation_euler.copy()
    hold_x = bpy.context.scene.render.resolution_x
    hold_y = bpy.context.scene.render.resolution_y 
    hold_filepath = bpy.context.scene.render.filepath
    
    # Find objects that are hidden in viewport and hide them in render
    tempHidden = []
    for o in bpy.data.objects:
        if o.hide_get() == True:
            o.hide_render = True
            tempHidden.append(o)
    
    # Change Settings
    bpy.context.scene.render.resolution_y = tool.resolution
    bpy.context.scene.render.resolution_x = tool.resolution
    switchback = False
    if bpy.ops.view3d.camera_to_view.poll():
        bpy.ops.view3d.camera_to_view()
        switchback = True
    
    # Ensure outputfile is set to png (temporarily, at least)
    previousFileFormat = scene.render.image_settings.file_format
    if scene.render.image_settings.file_format != 'PNG':
        scene.render.image_settings.file_format = 'PNG'
    
    filename = str(random.randint(0,100000000000))+".png"
    filepath = str(os.path.abspath(os.path.join(os.sep, 'tmp', filename)))
    bpy.context.scene.render.filepath = filepath
    
    #Render File, Mark Asset and Set Image
    bpy.ops.render.render(write_still = True)
    ob.asset_mark()
    override = bpy.context.copy()
    override['id'] = ob
    bpy.ops.ed.lib_id_load_custom_preview(override,filepath=filepath)
    
    # Unhide the objects hidden for the render
    for o in tempHidden:
        o.hide_render = False
    # Reset output file format
    scene.render.image_settings.file_format = previousFileFormat
    
    #Cleanup
    os.unlink(filepath)
    bpy.context.scene.render.resolution_y = hold_y
    bpy.context.scene.render.resolution_x = hold_x
    camera.location = hold_camerapos
    camera.rotation_euler = hold_camerarot
    bpy.context.scene.render.filepath = hold_filepath
    if switchback:
        bpy.ops.view3d.view_camera()


class OT_AssetSnapshotCollection(Operator):
    """Create a preview of a collection"""
    bl_idname = "view3d.asset_snaphot_collection"
    bl_label = "Asset Snapshot - Collection"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        snapshot(self, context,context.collection)
        return {'FINISHED'}


class OT_AssetSnapshotObject(Operator):
    """Create an asset preview of an object"""
    bl_idname = "view3d.object_preview"
    bl_label = "Asset Snapshot - Object"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        snapshot(self, context, bpy.context.view_layer.objects.active)
        return {'FINISHED'}


class OT_AssetDownloaderOperator(Operator):
    bl_label = "Run script"
    bl_idname = "alt.assetdownloader"
    def execute(self, context):
        tool = context.scene.assetlibrarytools
        ur = bpy.utils.user_resource('SCRIPTS')
        # Do some input checking
        if tool.downloader_save_path == '':
            DisplayMessageBox("Enter a save path", "Error", "ERROR")
        if ' ' in tool.downloader_save_path:
            DisplayMessageBox("Filepath invalid: space in filepath", "Error", "ERROR")
        if tool.keywordFilter == "":
            tool.keywordFilter = 'None'
        if ' ' not in tool.downloader_save_path and tool.downloader_save_path != '':
            # Start ALT_CC0AssetDownloader.py via chosen terminal
            if tool.terminal == 'xterm':
                os.system('xterm -e "python3 {0}/ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}"'.format(ur+'/addons/AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))
            if tool.terminal == 'konsole':
                os.system('konsole -e "python3 {0}/ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}"'.format(ur+'/addons/AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))
            if tool.terminal == 'gnome-terminal':
                os.system('gnome-terminal -e "python3 {0}/ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}"'.format(ur+'/addons/AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))
            if tool.terminal == 'cmd':
                os.system('start cmd /k \"cd /D {0} & python ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}'.format(ur+'\\addons\\AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))  
        return {'FINISHED'}


class OT_ImportSBSAR(Operator):
    bl_label = "Import SBSAR files"
    bl_idname = "alt.importsbsar"
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        p = pathlib.Path(str(tool.sbsar_import_path))
        i = 0 # number of files imported
        files = [x for x in p.glob('**/*.sbsar') if x.is_file()] # Get filepaths of files with the extension .sbsar in the selected directory (and subdirs, recursively)
        for f in files:
            try:
                bpy.ops.substance.load_sbsar(filepath=str(f), description_arg=True, files=[{"name":f.name, "name":f.name}], directory=str(f).replace(f.name, ""))
                i += 1
            except:
                print("SBSAR import failure")
        DisplayMessageBox("Complete, {0} sbsar files imported".format(i))
        return{'FINISHED'}


# ------------------------------------------------------------------------
#    UI
# ------------------------------------------------------------------------

class OBJECT_PT_panel(Panel):
    bl_label = "AssetLibraryTools"
    bl_idname = "OBJECT_PT_assetlibrarytools_panel"
    bl_category = "AssetLibraryTools"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    
    @classmethod
    def poll(self,context):
        return context.mode

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        tool = scene.assetlibrarytools
        obj = context.scene.assetlibrarytools
        
        
        # Material import UI
        matImportBox = layout.box()
        matImportRow = matImportBox.row()
        matImportRow.prop(obj, "matImport_expanded",
            icon="TRIA_DOWN" if obj.matImport_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        matImportRow.label(text="Batch import PBR texture sets as simple materials")
        if obj.matImport_expanded:
            matImportBox.prop(tool, "mat_import_path")
            matImportBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            matImportBox.operator("alt.batchimportpbr")
            matImportOptionsRow = matImportBox.row()
            matImportOptionsRow.prop(obj, "matImportOptions_expanded",
                icon="TRIA_DOWN" if obj.matImportOptions_expanded else "TRIA_RIGHT",
                icon_only=True, emboss=False
            )
            matImportOptionsRow.label(text="Import options: ")
            if obj.matImportOptions_expanded:
                matImportOptionsRow = matImportBox.row()
                matImportBox.label(text="Import settings:")
                matImportBox.prop(tool, "skip_existing")
                matImportBox.separator()
                matImportBox.label(text="Material settings:")
                matImportBox.prop(tool, "use_fake_user")
                matImportBox.prop(tool, "use_real_displacement")
                matImportBox.prop(tool, "texture_mapping")
                matImportBox.separator()
                matImportBox.label(text="Import following textures into materials (if found):")
                matImportBox.prop(tool, "import_diff")
                matImportBox.prop(tool, "import_sss")
                matImportBox.prop(tool, "import_met")
                matImportBox.prop(tool, "import_spec")
                matImportBox.prop(tool, "import_rough")
                matImportBox.prop(tool, "import_emission")
                matImportBox.prop(tool, "import_alpha")
                matImportBox.prop(tool, "import_norm")
                matImportBox.prop(tool, "import_disp")
        
        
        # Model import UI
        modelImportBox = layout.box()
        modelImportRow = modelImportBox.row()
        modelImportRow.prop(obj, "modelImport_expanded",
            icon="TRIA_DOWN" if obj.modelImport_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        modelImportRow.label(text="Batch import 3D models")
        if obj.modelImport_expanded:
            modelImportBox.prop(tool, "model_import_path")
            modelImportBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            modelImportBox.operator("alt.importmodels")
            modelImportOptionsRow = modelImportBox.row()
            modelImportOptionsRow.prop(obj, "modelImportOptions_expanded",
                icon="TRIA_DOWN" if obj.modelImportOptions_expanded else "TRIA_RIGHT",
                icon_only=True, emboss=False
            )
            modelImportOptionsRow.label(text="Import options: ")
            if obj.modelImportOptions_expanded:
                modelImportOptionsRow = modelImportBox.row()
                modelImportBox.label(text="Model options:")
                modelImportBox.prop(tool, "hide_after_import")
                modelImportBox.separator()
                modelImportBox.label(text="Search for and import the following filetypes:")
                modelImportBox.prop(tool, "import_fbx")
                modelImportBox.prop(tool, "import_gltf")
                modelImportBox.prop(tool, "import_obj")
                modelImportBox.prop(tool, "import_x3d")
        
        
        # Append from other .blend UI
        appendBox = layout.box()
        appendRow = appendBox.row()
        appendRow.prop(obj, "append_expanded",
            icon="TRIA_DOWN" if obj.append_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        appendRow.label(text="Batch append from .blend files")
        if obj.append_expanded:
            appendBox.prop(tool, "append_path")
            appendBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            appendBox.prop(tool, "append_recursive_search")
            appendBox.prop(tool, "appendType")
            if obj.appendType == 'objects':
                appendBox.prop(tool, "deleteLights")
                appendBox.prop(tool, "deleteCameras")
            appendBox.operator("alt.batchappend")
            
            
        # Asset browser operations UI
        assetBrowserOpsBox = layout.box()
        assetBrowserOpsRow = assetBrowserOpsBox.row()
        assetBrowserOpsRow.prop(obj, "assetBrowserOpsRow_expanded",
            icon="TRIA_DOWN" if obj.assetBrowserOpsRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        assetBrowserOpsRow.label(text="Asset browser operations")
        if obj.assetBrowserOpsRow_expanded:
            assetBrowserOpsRow = assetBrowserOpsBox.row()
            assetBrowserOpsBox.label(text="Batch mark/unmark assets:")
            assetBrowserOpsBox.prop(tool, "markunmark")
            assetBrowserOpsBox.prop(tool, "assettype")
            assetBrowserOpsBox.operator("alt.manageassets")
            assetBrowserOpsBox.label(text="Generate asset previews:")
            assetBrowserOpsBox.prop(tool, "previewgentype")
            assetBrowserOpsBox.operator("alt.generateassetpreviews")
            
        
        
        # Utility operations UI
        utilBox = layout.box()
        utilRow = utilBox.row()
        utilRow.prop(obj, "utilRow_expanded",
            icon="TRIA_DOWN" if obj.utilRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        utilRow.label(text="Utilities")
        if obj.utilRow_expanded:
            utilRow = utilBox.row()
            utilBox.prop(tool, "deleteType")
            utilBox.operator("alt.batchdelete")
            utilBox.separator()
            utilBox.label(text='Deletes based on material name, not material contents', icon="ERROR")
            utilBox.operator("alt.simpledeldupemats")
            utilBox.operator("alt.cleanupunusedmats")
            utilBox.separator()
            utilBox.prop(tool, "dispNewScale")
            utilBox.operator("alt.changealldispscale")
            utilBox.operator("alt.userealdispall")
        
        
        #Asset snapshot UI
        snapshotBox = layout.box()
        snapshotRow = snapshotBox.row()
        snapshotRow.prop(obj, "snapshotRow_expanded",
            icon="TRIA_DOWN" if obj.snapshotRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        snapshotRow.label(text="Asset snapshot")
        if obj.snapshotRow_expanded:
            snapshotBox.label(text='Sometimes crashes. SAVE YOUR FILES', icon="ERROR")
            snapshotBox.prop(tool, "resolution")
            snapshotBox.operator("view3d.object_preview")
            snapshotBox.operator("view3d.asset_snaphot_collection")
        
        
        # Asset downloader UI
        assetDownloaderBox = layout.box()
        assetDownloaderRow = assetDownloaderBox.row()
        assetDownloaderRow.prop(obj, "assetDownloaderRow_expanded",
            icon="TRIA_DOWN" if obj.assetDownloaderRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        assetDownloaderRow.label(text="Batch asset downloader [EXPERIMENTAL]")
        if obj.assetDownloaderRow_expanded:
            assetDownloaderRow = assetDownloaderBox.row()
            assetDownloaderBox.label(text='Downloads files from ambientcg.com')
            assetDownloaderBox.prop(tool, "downloader_save_path")
            assetDownloaderBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            assetDownloaderBox.prop(tool, "keywordFilter")
            assetDownloaderBox.prop(tool, "showAllDownloadAttribs")
            assetDownloaderBox.prop(tool, "attributeFilter")
            assetDownloaderBox.prop(tool, "extensionFilter")
            assetDownloaderBox.prop(tool, "unZip")
            assetDownloaderBox.prop(tool, "deleteZips")
            assetDownloaderBox.prop(tool, "skipDuplicates")
            assetDownloaderBox.prop(tool, "terminal")
            assetDownloaderBox.operator("alt.assetdownloader")
            
        
         # SBSAR import UI
        sbsarImportBox = layout.box()
        sbsarImportRow = sbsarImportBox.row()
        sbsarImportRow.prop(obj, "sbsarImport_expanded",
            icon="TRIA_DOWN" if obj.sbsarImport_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        sbsarImportRow.label(text="Batch import SBSAR files [EXPERIMENTAL]")
        if obj.sbsarImport_expanded:
            sbsarImportBox.label(text="Requires adobe substance 3D add-on for Blender", icon="ERROR")
            sbsarImportBox.prop(tool, "sbsar_import_path")
            sbsarImportBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            sbsarImportBox.operator("alt.importsbsar")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    properties,
    OT_BatchImportPBR,
    OT_ImportModels,
    OT_BatchAppend,
    OT_ManageAssets,
    OT_GenerateAssetPreviews,
    OT_BatchDelete,
    OT_SimpleDelDupeMaterials,
    OT_CleanupUnusedMaterials,
    OT_UseDisplacementOnAll,
    OT_ChangeAllDisplacementScale,
    OT_AssetSnapshotCollection,
    OT_AssetSnapshotObject,
    OT_AssetDownloaderOperator,
    OT_ImportSBSAR,
    OBJECT_PT_panel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.assetlibrarytools = PointerProperty(type=properties)
    
def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.assetlibrarytools

if __name__ == "__main__":
    register()
