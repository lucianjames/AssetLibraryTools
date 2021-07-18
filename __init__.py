bl_info = {
    "name": "AssetLibraryTools",
    "description": "Set of tools to speed up the creation of asset libraries for the asset browser introduced in blender 3.0",
    "author": "Lucian James (LJ3D)",
    "version": (0, 0, 5),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
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
metNames = ["metallic", "metalness", "metal", "mtl"]
specNames = ["specularity", "specular", "spec", "spc"]
roughNames = ["roughness", "rough", "rgh"]
glossNames = ["gloss", "glossy", "glossiness"]
normNames = ["normal", "nor", "nrm", "nrml norm"]
bumpNames = ["bump", "bmp"]
dispNames = ["displacement", "displace", "disp", "dsp", "height", "heightmap"]

# Function partly stolen from node wrangler :D
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
        if i in glossNames:
            PBRTT = "gloss"
        if i in normNames:
            PBRTT = "norm"
        if i in bumpNames:
            PBRTT = "bump"
        if i in dispNames:
            PBRTT = "disp"
    return PBRTT

def DisplayMessageBox(message = "", title = "Info", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


# ------------------------------------------------------------------------
#    AssetLibraryTools PBR import class
# ------------------------------------------------------------------------ 

class createPBR():
    
    def simplePrincipledSetup(name, files):
        
        tool = bpy.context.scene.assetlibrarytools
        
        # Create a new material
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear all nodes to start clean
        nodes.clear()
            
        # Create output node
        node_output = nodes.new(type='ShaderNodeOutputMaterial')   
        node_output.name = "node_output"
        node_output.location = 250,0
        
        # Create principled BSDF node
        node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        node_principled.name = "node_principled"
        node_principled.location = -300,0
            
        # Create mapping nodes
        node_mapping = nodes.new(type="ShaderNodeMapping")
        node_mapping.name = "node_mapping"
        node_mapping.location = -1300,0
        node_texCoord = nodes.new(type="ShaderNodeTexCoord")
        node_texCoord.name = "node_texCoord"
        node_texCoord.location = -1500,0
            
        # Link base nodes
        links.new(node_principled.outputs[0], node_output.inputs[0])
        links.new(node_texCoord.outputs[2], node_mapping.inputs[0])

        # Create texture nodes
        node_imTexDiffuse = nodes.new(type="ShaderNodeTexImage")
        node_imTexDiffuse.location = -800,300
        node_imTexDiffuse.name = "node_imTexDiffuse"
        node_imTexMetallic = nodes.new(type="ShaderNodeTexImage")
        node_imTexMetallic.location = -800,0
        node_imTexDiffuse.name = "node_imTexMetallic"
        node_imTexRoughness = nodes.new(type="ShaderNodeTexImage")
        node_imTexRoughness.location = -800,-300
        node_imTexRoughness.name = "node_imTexRoughness"
        node_imTexNormal = nodes.new(type="ShaderNodeTexImage")
        node_imTexNormal.location = -800,-600
        node_imTexNormal.name = "node_imTexNormal"
        node_imTexDisplacement = nodes.new(type="ShaderNodeTexImage")
        node_imTexDisplacement.location = -800,-900
        node_imTexDisplacement.name = "node_imTexDisplacement"
        
        # Create norm+disp nodes
        node_normalMap = nodes.new(type="ShaderNodeNormalMap")
        node_normalMap.location = -500,-600
        node_normalMap.name = "node_normalMap"
        node_displacement = nodes.new(type="ShaderNodeDisplacement")
        node_displacement.location = -200,-600
        node_displacement.name = "node_displacement"
        
        # Load textures
        diffuseTexture = None
        metallicTexture = None
        roughnessTexture = None
        normalTexture = None
        displacementTexture = None
        for i in files:
            t = FindPBRTextureType(i.name)
            if t == "diff":
                diffuseTexture = bpy.data.images.load(str(i))
            elif t == "met":
                metallicTexture = bpy.data.images.load(str(i))
                metallicTexture.colorspace_settings.name = 'Non-Color'
            elif t == "rough":
                roughnessTexture = bpy.data.images.load(str(i))
                roughnessTexture.colorspace_settings.name = 'Non-Color'
            elif t == "norm":
                normalTexture = bpy.data.images.load(str(i))
                normalTexture.colorspace_settings.name = 'Non-Color'
            elif t == "disp":
                displacementTexture = bpy.data.images.load(str(i))
                displacementTexture.colorspace_settings.name = 'Non-Color'
                
        '''check if texture is loaded
            if not loaded, delete relevant node(s)
            if loaded, place texture in relevant texture node and link relevant nodes'''
            
        if diffuseTexture != None and tool.import_diff != False:
            node_imTexDiffuse.image = diffuseTexture
            links.new(node_imTexDiffuse.outputs[0], node_principled.inputs[0])
            links.new(node_mapping.outputs[0], node_imTexDiffuse.inputs[0])
        else:
            nodes.remove(node_imTexDiffuse)
            
        if metallicTexture != None and tool.import_met != False:
            node_imTexMetallic.image = metallicTexture
            links.new(node_imTexMetallic.outputs[0], node_principled.inputs[4])
            links.new(node_mapping.outputs[0], node_imTexMetallic.inputs[0])
        else:
            nodes.remove(node_imTexMetallic)
            
        if roughnessTexture != None and tool.import_rough != False:
            node_imTexRoughness.image = roughnessTexture
            links.new(node_imTexRoughness.outputs[0], node_principled.inputs[7])
            links.new(node_mapping.outputs[0], node_imTexRoughness.inputs[0])
        else:
            nodes.remove(node_imTexRoughness)
            
        if normalTexture != None and tool.import_norm != False:
            node_imTexNormal.image = normalTexture
            links.new(node_imTexNormal.outputs[0], node_normalMap.inputs[1])
            links.new(node_normalMap.outputs[0], node_principled.inputs[20])
            links.new(node_mapping.outputs[0], node_imTexNormal.inputs[0])
        else:
            nodes.remove(node_imTexNormal)
            nodes.remove(node_normalMap)
            
        if displacementTexture != None and tool.import_disp != False:
            node_imTexDisplacement.image = displacementTexture
            links.new(node_imTexDisplacement.outputs[0], node_displacement.inputs[0])
            links.new(node_displacement.outputs[0], node_output.inputs[2])
            links.new(node_mapping.outputs[0], node_imTexDisplacement.inputs[0])
        else:
            nodes.remove(node_imTexDisplacement)
            nodes.remove(node_displacement)
        
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
    model_import_path : StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import models from.\nSubdirectories are checked recursively.",
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
    import_met : BoolProperty(
        name = "Import metallic",
        description = "",
        default = True
        )
    import_rough : BoolProperty(
        name = "Import roughness",
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
        name = "Hide models after they are imported",
        description = "Reduces viewport polycount, prevents low framerate/crashes",
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
        name="Attribute filter:",
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
        name="Extension filter:",
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
    batchOpsRow_expanded : BoolProperty(
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
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        old_objects = set(context.scene.objects)
        p = pathlib.Path(str(tool.model_import_path))
        i = 0
        # Import FBX files
        if tool.import_fbx == True:
            fbxFilePaths = [x for x in p.glob('**/*.fbx') if x.is_file()]
            for filePath in fbxFilePaths:
                bpy.ops.import_scene.fbx(filepath=str(filePath))
                i += 1
        # Import GLTF files
        if tool.import_gltf == True:
            gltfFilePaths = [x for x in p.glob('**/*.gltf') if x.is_file()]
            for filePath in gltfFilePaths:
                bpy.ops.import_scene.gltf(filepath=str(filePath))
                i += 1
        # Import OBJ files
        if tool.import_obj == True:
            objFilePaths = [x for x in p.glob('**/*.obj') if x.is_file()]
            for filePath in objFilePaths:
                bpy.ops.import_scene.obj(filepath=str(filePath))
                i += 1
        # Import X3D files
        if tool.import_x3d == True:
            x3dFilePaths = [x for x in p.glob('**/*.x3d') if x.is_file()]
            for filePath in x3dFilePaths:
                bpy.ops.import_scene.x3d(filepath=str(filePath))
                i += 1
        '''
        Hide objects after importing them if user wants
        Hiding them individually straight after import might be a better idea
        '''
        imported_objects = set(context.scene.objects) - old_objects
        if tool.hide_after_import == True:
            for object in imported_objects:
                object.hide_set(True)
        DisplayMessageBox("Complete, {0} models imported".format(i))
        return{'FINISHED'}

class OT_ImportPbrTextureSets(Operator):
    bl_label = "Import PBR textures"
    bl_idname = "alt.importpbrtexturesets"
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        i = 0
        subdirectories = [x for x in pathlib.Path(tool.mat_import_path).iterdir() if x.is_dir()]
        for sd in subdirectories:
            filePaths = [x for x in pathlib.Path(sd).iterdir() if x.is_file()]
            mat = createPBR.simplePrincipledSetup(sd.name, filePaths)
            if tool.use_fake_user == True:
                mat.use_fake_user = True
            if tool.use_real_displacement == True:
                mat.cycles.displacement_method = 'BOTH'
            i += 1
        DisplayMessageBox("Complete, {0} materials imported".format(i))
        return{'FINISHED'}

class OT_MarkAllMaterialsAsAssets(Operator):
    bl_label = "Mark all materials as assets"
    bl_idname = "alt.markallmaterialssasassets"
    
    def execute(self, context):
        i = 0
        for mat in bpy.data.materials:
            mat.asset_mark()
            i += 1
        DisplayMessageBox("Complete, {0} assets marked".format(i))
        return {'FINISHED'}

class OT_ClearMaterialAssets(Operator):
    bl_label = "Unmark all material assets"
    bl_idname = "alt.clearmaterialassets"
    
    def execute(self, context):
        i = 0
        for mat in bpy.data.materials:
            mat.asset_clear()
            i += 1
        DisplayMessageBox("Complete, {0} assets unmarked".format(i))
        return {'FINISHED'}

class OT_MarkAllMeshesAsAssets(Operator):
    bl_label = "Mark all meshes as assets"
    bl_idname = "alt.markallmeshesasassets"
    
    def execute(self, context):
        i = 0
        for mesh in bpy.data.meshes:
            mesh.asset_mark()
            i += 1
        DisplayMessageBox("Complete, {0} assets marked".format(i))
        return {'FINISHED'}

class OT_ClearMeshAssets(Operator):
    bl_label = "Unmark all mesh assets"
    bl_idname = "alt.clearmeshassets"
    
    def execute(self, context):
        i = 0
        for mesh in bpy.data.meshes:
            mesh.asset_clear()
            i += 1
        DisplayMessageBox("Complete, {0} assets unmarked".format(i))
        return {'FINISHED'}

class OT_MarkAllObjectsAsAssets(Operator):
    bl_label = "Mark all objects as assets"
    bl_idname = "alt.markallobjectsasassets"
    
    def execute(self, context):
        i = 0
        for object in bpy.data.objects:
            object.asset_mark()
            i += 1
        DisplayMessageBox("Complete, {0} assets marked".format(i))
        return {'FINISHED'}

class OT_ClearObjectAssets(Operator):
    bl_label = "Unmark all object assets"
    bl_idname = "alt.clearobjectassets"
    
    def execute(self, context):
        i = 0
        for object in bpy.data.objects:
            object.asset_clear()
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
        os.system('start cmd /k \"cd /D {0} & python ALT_CC0AssetDownloader.py {1} {2} {3} {4} {5} {6}'.format(ur+'\\addons\\AssetLibraryTools', tool.downloader_save_path, tool.keywordFilter, tool.attributeFilter, tool.extensionFilter, str(tool.unZip), str(tool.deleteZips)))
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
            matImportBox.label(text='Make sure to uncheck "Relative Path"!')
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
                matImportBox.prop(tool, "import_met")
                matImportBox.prop(tool, "import_rough")
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
            modelImportBox.label(text='Make sure to uncheck "Relative Path"!')
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
        
        
        # Other batch operations UI
        batchOpBox = layout.box()
        batchOpsRow = batchOpBox.row()
        batchOpsRow.prop(obj, "batchOpsRow_expanded",
            icon="TRIA_DOWN" if obj.batchOpsRow_expanded else "TRIA_RIGHT",
            icon_only=True, emboss=False
        )
        batchOpsRow.label(text="Batch mark/clear operations")
        if obj.batchOpsRow_expanded:
            batchOpsRow = batchOpBox.row()
            batchOpBox.label(text="Batch mark/clear operations")
            batchOpBox.operator("alt.markallmaterialssasassets")
            batchOpBox.operator("alt.clearmaterialassets")
            batchOpBox.separator()
            batchOpBox.operator("alt.markallmeshesasassets")
            batchOpBox.operator("alt.clearmeshassets")
            batchOpBox.separator()
            batchOpBox.operator("alt.markallobjectsasassets")
            batchOpBox.operator("alt.clearobjectassets")
        
        
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
            assetDownloaderBox.prop(tool, "keywordFilter")
            assetDownloaderBox.prop(tool, "attributeFilter")
            assetDownloaderBox.prop(tool, "extensionFilter")
            assetDownloaderBox.prop(tool, "unZip")
            assetDownloaderBox.prop(tool, "deleteZips")
            assetDownloaderBox.operator("alt.assetdownloader")
            

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    properties,
    OT_ImportModels,
    OT_ImportPbrTextureSets,
    OT_MarkAllMaterialsAsAssets,
    OT_ClearMaterialAssets,
    OT_MarkAllMeshesAsAssets,
    OT_ClearMeshAssets,
    OT_MarkAllObjectsAsAssets,
    OT_ClearObjectAssets,
    OT_DeleteAllMaterials,
    OT_DeleteAllObjects,
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
