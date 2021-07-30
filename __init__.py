bl_info = {
    "name": "AssetLibraryTools",
    "description": "AssetLibraryTools is a free addon which aims to speed up the process of creating asset libraries with the asset browser, This addon is currently very much experimental as is the asset browser in blender.",
    "author": "Lucian James (LJ3D)",
    "version": (0, 1, 4),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
    "warning": "Developed in 3.0 ALPHA. May be unstable or broken in future versions", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
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


# ------------------------------------------------------------------------
#    Stuff
# ------------------------------------------------------------------------ 

diffNames = ["diffuse", "diff", "albedo", "base", "col", "color"]
sssNames = ["sss", "subsurface"]
metNames = ["metallic", "metalness", "metal", "mtl", "met"]
specNames = ["specularity", "specular", "spec", "spc"]
roughNames = ["roughness", "rough", "rgh", "gloss", "glossy", "glossiness"]
normNames = ["normal", "nor", "nrm", "nrml norm"]
dispNames = ["displacement", "displace", "disp", "dsp", "height", "heightmap", "bump", "bmp"]
alphaNames = ["alpha", "opacity"]
emissiveNames = ["emissive", "emission"]

def FindPBRTextureType(fname):
    # Split filename into components
    # 'WallTexture_diff_2k.002.jpg' -> ['Wall', 'Texture', 'diff', 'k']
    # Remove digits
    fname = ''.join(i for i in fname if not i.isdigit())
    # Separate CamelCase by space
    fname = re.sub("([a-z])([A-Z])","\g<1> \g<2>",fname)
    # Replace common separators with SPACE
    seperators = ['_', '.', '-', '__', '--', '#']
    for sep in seperators:
        fname = fname.replace(sep, ' ')
    components = fname.split(' ')
    components = [c.lower() for c in components]
    
    # This is probably not the best way to do this lol
    PBRTT = None
    for i in components:
        if i in diffNames:
            PBRTT = "diff"
        if i in sssNames:
            PBRTT = "sss"
        if i in metNames:
            PBRTT = "met"
        if i in specNames:
            PBRTT = "spec"
        if i in roughNames:
            PBRTT = "rough"
        if i in normNames:
            PBRTT = "norm"
        if i in dispNames:
            PBRTT = "disp"
        if i in alphaNames:
            PBRTT = "alpha"
        if i in emissiveNames:
            PBRTT = "emission"
    print(PBRTT)
    return PBRTT

def DisplayMessageBox(message = "", title = "Info", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


# ------------------------------------------------------------------------
#    AssetLibraryTools PBR import class
# ------------------------------------------------------------------------ 

class createPBR():
    
    def createNode(mat, type, name="newNode", location=(0,0)):
        nodes = mat.node_tree.nodes
        n = nodes.new(type=type)
        n.name = name
        n.location = location
        return n
    
    def simplePrincipledSetup(name, files):
        tool = bpy.context.scene.assetlibrarytools
        # Create a new empty material
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links 
        nodes.clear()
        
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
        node_output = createPBR.createNode(mat, "ShaderNodeOutputMaterial", "node_output", (250,0))
        node_principled = createPBR.createNode(mat, "ShaderNodeBsdfPrincipled", "node_principled", (-300,0))
        node_mapping = createPBR.createNode(mat, "ShaderNodeMapping", "node_mapping", (-1300,0))
        node_texCoord = createPBR.createNode(mat, "ShaderNodeTexCoord", "node_texCoord", (-1500,0))
        # Link base nodes
        links.new(node_principled.outputs[0], node_output.inputs[0])
        links.new(node_texCoord.outputs[2], node_mapping.inputs[0])
        
        # Create, fill, and link texture nodes
        imported_tex_nodes = 0
        if diffuseTexture != None and tool.import_diff != False:
            node_imTexDiffuse = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexDiffuse", (-800,300-(300*imported_tex_nodes)))
            node_imTexDiffuse.image = diffuseTexture
            links.new(node_imTexDiffuse.outputs[0], node_principled.inputs[0])
            links.new(node_mapping.outputs[0], node_imTexDiffuse.inputs[0])
            imported_tex_nodes += 1
            
        if sssTexture != None and tool.import_sss != False:
            node_imTexSSS = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexSSS", (-800,300-(300*imported_tex_nodes)))
            node_imTexSSS.image = sssTexture
            links.new(node_imTexSSS.outputs[0], node_principled.inputs[1])
            links.new(node_mapping.outputs[0], node_imTexSSS.inputs[0])
            imported_tex_nodes += 1
            
        if metallicTexture != None and tool.import_met != False:
            node_imTexMetallic = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexMetallic", (-800,300-(300*imported_tex_nodes)))
            node_imTexMetallic.image = metallicTexture
            links.new(node_imTexMetallic.outputs[0], node_principled.inputs[4])
            links.new(node_mapping.outputs[0], node_imTexMetallic.inputs[0])
            imported_tex_nodes += 1
            
        if specularTexture != None and tool.import_spec != False:
            node_imTexSpecular = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexSpecular", (-800,300-(300*imported_tex_nodes)))
            node_imTexSpecular.image = specularTexture
            links.new(node_imTexSpecular.outputs[0], node_principled.inputs[5])
            links.new(node_mapping.outputs[0], node_imTexSpecular.inputs[0])
            imported_tex_nodes += 1
            
        if roughnessTexture != None and tool.import_rough != False:
            node_imTexRoughness = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexRoughness", (-800,300-(300*imported_tex_nodes)))
            node_imTexRoughness.image = roughnessTexture
            links.new(node_imTexRoughness.outputs[0], node_principled.inputs[7])
            links.new(node_mapping.outputs[0], node_imTexRoughness.inputs[0])
            imported_tex_nodes += 1
            
        if emissionTexture != None and tool.import_emission != False:
            node_imTexEmission = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexEmission", (-800,300-(300*imported_tex_nodes)))
            node_imTexEmission.image = emissionTexture
            links.new(node_imTexEmission.outputs[0], node_principled.inputs[17])
            links.new(node_mapping.outputs[0], node_imTexEmission.inputs[0])
            imported_tex_nodes += 1
            
        if alphaTexture != None and tool.import_alpha != False:
            node_imTexAlpha = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexAlpha", (-800,300-(300*imported_tex_nodes)))
            node_imTexAlpha.image = alphaTexture
            links.new(node_imTexAlpha.outputs[0], node_principled.inputs[19])
            links.new(node_mapping.outputs[0], node_imTexAlpha.inputs[0])
            imported_tex_nodes += 1
            
        if normalTexture != None and tool.import_norm != False:
            node_imTexNormal = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexNormal", (-800,300-(300*imported_tex_nodes)))
            node_imTexNormal.image = normalTexture
            node_normalMap = createPBR.createNode(mat, "ShaderNodeNormalMap", "node_normalMap", (-500,300-(300*imported_tex_nodes)))
            links.new(node_imTexNormal.outputs[0], node_normalMap.inputs[1])
            links.new(node_normalMap.outputs[0], node_principled.inputs[20])
            links.new(node_mapping.outputs[0], node_imTexNormal.inputs[0])
            imported_tex_nodes += 1
            
        if displacementTexture != None and tool.import_disp != False:
            node_imTexDisplacement = createPBR.createNode(mat, "ShaderNodeTexImage", "node_imTexDisplacement", (-800,300-(300*imported_tex_nodes)))
            node_imTexDisplacement.image = displacementTexture
            node_displacement = createPBR.createNode(mat, "ShaderNodeDisplacement", "node_displacement", (-200,-600))
            links.new(node_imTexDisplacement.outputs[0], node_displacement.inputs[0])
            links.new(node_displacement.outputs[0], node_output.inputs[2])
            links.new(node_mapping.outputs[0], node_imTexDisplacement.inputs[0])
            imported_tex_nodes += 1
        
        return mat


# ------------------------------------------------------------------------
#    Properties
# ------------------------------------------------------------------------ 

class properties(PropertyGroup):
    
    # Import paths
    mat_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import PBR texture sets from.\nFormat your files like this: ChosenDirectory/PBRTextureName/textureFiles",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    sbsar_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import sbsar files from.\nSubdirectories are checked recursively",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    model_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import models from.\nSubdirectories are checked recursively",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    
    
    # Material import options
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
    attributeFilter : EnumProperty(
        name="Attribute filter",
        description="Choose attribute to filter assets by",
        items=[ ('None', "None", ""),
                ('1K-JPG', "1K-JPG", ""),
                ('2K-JPG', "2K-JPG", ""),
                ('4K-JPG', "4K-JPG", ""),
                ('8K-JPG', "8K-JPG", ""),
                ('1K-PNG', "1K-PNG", ""),
                ('2K-PNG', "2K-PNG", ""),
                ('4K-PNG', "4K-PNG", ""),
                ('8K-PNG', "8K-PNG", ""),
               ]
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
    terminal : EnumProperty(
        name="Terminal",
        description="Choose terminal to run script with",
        items=[ ('cmd', "cmd", ""),
                ('gnome-terminal', "gnome-terminal", ""),
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
    sbsarImport_expanded : BoolProperty(
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
    assetMngmtRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    utilRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )
    assetDownloaderRow_expanded : BoolProperty(
        name = "Click to expand",
        description = "",
        default = False
        )


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class OT_ImportModels(Operator):
    bl_label = "Import models"
    bl_idname = "alt.importmodels"
    
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
        i = 0
        # Import FBX files
        if tool.import_fbx == True:
            fbxFilePaths = [x for x in p.glob('**/*.fbx') if x.is_file()]
            for filePath in fbxFilePaths:
                old_objects = set(context.scene.objects)
                bpy.ops.import_scene.fbx(filepath=str(filePath))
                OT_ImportModels.hideNewObjects(old_objects)
                i += 1
        # Import GLTF files
        if tool.import_gltf == True:
            gltfFilePaths = [x for x in p.glob('**/*.gltf') if x.is_file()]
            for filePath in gltfFilePaths:
                old_objects = set(context.scene.objects)
                bpy.ops.import_scene.gltf(filepath=str(filePath))
                OT_ImportModels.hideNewObjects(old_objects)
                i += 1
        # Import OBJ files
        if tool.import_obj == True:
            objFilePaths = [x for x in p.glob('**/*.obj') if x.is_file()]
            for filePath in objFilePaths:
                old_objects = set(context.scene.objects)
                bpy.ops.import_scene.obj(filepath=str(filePath))
                OT_ImportModels.hideNewObjects(old_objects)
                i += 1
        # Import X3D files
        if tool.import_x3d == True:
            x3dFilePaths = [x for x in p.glob('**/*.x3d') if x.is_file()]
            for filePath in x3dFilePaths:
                old_objects = set(context.scene.objects)
                bpy.ops.import_scene.x3d(filepath=str(filePath))
                OT_ImportModels.hideNewObjects(old_objects)
                i += 1
        DisplayMessageBox("Complete, {0} models imported".format(i))
        return{'FINISHED'}

class OT_ImportPbrTextureSets(Operator):
    bl_label = "Import PBR textures"
    bl_idname = "alt.importpbrtexturesets"
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        i = 0
        i2 = 0
        subdirectories = [x for x in pathlib.Path(tool.mat_import_path).iterdir() if x.is_dir()]
        for sd in subdirectories:
            filePaths = [x for x in pathlib.Path(sd).iterdir() if x.is_file()]
            mat = createPBR.simplePrincipledSetup(sd.name, filePaths)
            if tool.use_fake_user == True:
                mat.use_fake_user = True
            if tool.use_real_displacement == True:
                mat.cycles.displacement_method = 'BOTH'
            # Delete the material if it contains no textures
            hasTex = False
            for n in mat.node_tree.nodes:
                if n.type == 'TEX_IMAGE':
                    hasTex = True
            if hasTex == False:
                bpy.data.materials.remove(mat)
                i2 += 1
            else:
                i += 1
        if i2 > 0:
            DisplayMessageBox("Complete, {0} materials imported, {1} imported material(s) were deleted after import because they contained no textures".format(i,i2))
        else:
            DisplayMessageBox("Complete, {0} materials imported".format(i))
        return{'FINISHED'}

class OT_ImportSBSAR(Operator):
    bl_label = "Import SBSAR files"
    bl_idname = "alt.importsbsar"
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        p = pathlib.Path(str(tool.sbsar_import_path))
        i = 0
        files = [x for x in p.glob('**/*.sbsar') if x.is_file()]
        for f in files:
            try:
                bpy.ops.substance.load_sbsar(filepath=str(f), description_arg=True, files=[{"name":f.name, "name":f.name}], directory=str(f).replace(f.name, ""))
                i += 1
                print("SBSAR import success")
            except:
                print("SBSAR import failure")
        DisplayMessageBox("Complete, {0} sbsar files imported".format(i))
        return{'FINISHED'}







class OT_ManageAssets(Operator):
    bl_label = "Go"
    bl_idname = "alt.manageassets"
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        i = 0
        
        # IF statement hell
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

class OT_DeleteAllMaterials(Operator):
    bl_label = "Delete all materials"
    bl_idname = "alt.deleteallmaterials"
    
    def execute(self, context):
        i = 0
        for mat in bpy.data.materials:
            bpy.data.materials.remove(mat)
            i += 1
        DisplayMessageBox("Complete, {0} materials deleted".format(i))
        return {'FINISHED'}

class OT_DeleteAllObjects(Operator):
    bl_label = "Delete all objects"
    bl_idname = "alt.deleteallobjects"
    
    def execute(self, context):
        i = 0
        for object in bpy.data.objects:
            bpy.data.objects.remove(object)
            i += 1
        DisplayMessageBox("Complete, {0} objects deleted".format(i))
        return {'FINISHED'}

class OT_DeleteAllMeshes(Operator):
    bl_label = "Delete all meshes"
    bl_idname = "alt.deleteallmeshes"
    
    def execute(self, context):
        i = 0
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
            i += 1
        DisplayMessageBox("Complete, {0} meshes deleted".format(i))
        return {'FINISHED'}

class OT_DeleteAllTextures(Operator):
    bl_label = "Delete all textures"
    bl_idname = "alt.deletealltextures"
    
    def execute(self, context):
        i = 0
        for tex in bpy.data.textures:
            bpy.data.textures.remove(tex)
            i += 1
        DisplayMessageBox("Complete, {0} textures deleted".format(i))
        return {'FINISHED'}
    
class OT_DeleteAllImages(Operator):
    bl_label = "Delete all images"
    bl_idname = "alt.deleteallimages"
    
    def execute(self, context):
        i = 0
        while len(bpy.data.images) > 0: # Cant use a for loop like the other "delete all" operations for some reason
            bpy.data.images.remove(bpy.data.images[0])
            i += 1
        DisplayMessageBox("Complete, {0} images deleted".format(i))
        return {'FINISHED'}

class OT_UseDisplacementOnAll(Operator):
    bl_label = "Use real displacement on all materials"
    bl_idname = "alt.userealdispall"
    
    def execute(self, context):
        for mat in bpy.data.materials:
            mat.cycles.displacement_method = 'BOTH'
        DisplayMessageBox("Done")
        return {'FINISHED'}

class OT_AssetDownloaderOperator(Operator):
    bl_label = "Run script"
    bl_idname = "alt.assetdownloader"
    
    def execute(self, context):
        tool = context.scene.assetlibrarytools
        ur = bpy.utils.user_resource('SCRIPTS')
        if tool.downloader_save_path == '':
            DisplayMessageBox("Invalid save path", "Warning", "ERROR")
        if tool.keywordFilter == "":
            tool.keywordFilter = 'None'
        
        if tool.terminal == 'gnome-terminal':
            os.system('gnome-terminal -e "python3 {0}/ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}"'.format(ur+'/addons/AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))
        if tool.terminal == 'cmd':
            os.system('start cmd /k \"cd /D {0} & python ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6} {7}'.format(ur+'\\addons\\AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips), str(tool.skipDuplicates)))  
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel in Object Mode
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
            matImportBox.operator("alt.importpbrtexturesets")
            matImportOptionsRow = matImportBox.row()
            matImportOptionsRow.prop(obj, "matImportOptions_expanded",
                icon="TRIA_DOWN" if obj.matImportOptions_expanded else "TRIA_RIGHT",
                icon_only=True, emboss=False
            )
            matImportOptionsRow.label(text="Import options: ")
            if obj.matImportOptions_expanded:
                matImportOptionsRow = matImportBox.row()
                matImportBox.label(text="Material settings:")
                matImportBox.prop(tool, "use_fake_user")
                matImportBox.prop(tool, "use_real_displacement")
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
                modelImportBox.label(text="Search for and import the following filetypes:")
                modelImportBox.prop(tool, "import_fbx")
                modelImportBox.prop(tool, "import_gltf")
                modelImportBox.prop(tool, "import_obj")
                modelImportBox.prop(tool, "import_x3d")
        
        
        # Asset management UI
        assetMngmtBox = layout.box()
        assetMngmtRow = assetMngmtBox.row()
        assetMngmtRow.prop(obj, "assetMngmtRow_expanded",
            icon="TRIA_DOWN" if obj.assetMngmtRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        assetMngmtRow.label(text="Asset browser operations")
        if obj.assetMngmtRow_expanded:
            assetMngmtRow = assetMngmtBox.row()
            assetMngmtBox.label(text="Batch mark/unmark assets:")
            assetMngmtBox.prop(tool, "markunmark")
            assetMngmtBox.prop(tool, "assettype")
            assetMngmtBox.operator("alt.manageassets")
        
        
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
            utilBox.operator("alt.deleteallmaterials")
            utilBox.operator("alt.deleteallobjects")
            utilBox.operator("alt.deleteallmeshes")
            utilBox.operator("alt.deletealltextures")
            utilBox.operator("alt.deleteallimages")
            utilBox.separator()
            utilBox.operator("alt.userealdispall")
            
        
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
            assetDownloaderBox.prop(tool, "downloader_save_path")
            assetDownloaderBox.label(text='Make sure to uncheck "Relative Path"!', icon="ERROR")
            assetDownloaderBox.prop(tool, "keywordFilter")
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
    OT_ImportModels,
    OT_ImportPbrTextureSets,
    OT_ImportSBSAR,
    OT_ManageAssets,
    OT_DeleteAllMaterials,
    OT_DeleteAllObjects,
    OT_DeleteAllMeshes,
    OT_DeleteAllTextures,
    OT_DeleteAllImages,
    OT_UseDisplacementOnAll,
    OT_AssetDownloaderOperator,
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
