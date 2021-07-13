bl_info = {
    "name": "AssetLibraryTools",
    "description": "Set of tools to speed up the creation of asset libraries with the asset browser introduced in blender 3.0",
    "author": "Lucian James (LJ3D)",
    "version": (0, 0, 3),
    "blender": (3, 0, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
    "category": ""
}

import bpy
import pathlib
import re
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


# ------------------------------------------------------------------------
#    AssetLibraryTools PBR import class
# ------------------------------------------------------------------------ 

class createPBR():   
    
    def simple(name, files):
        
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
        node_imTexDiffuse.location = -800,0
        node_imTexDiffuse.name = "node_imTexDiffuse"
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
        roughnessTexture = None
        normalTexture = None
        displacementTexture = None
        for i in files:
            t = FindPBRTextureType(i.name)
            if t == "diff":
                diffuseTexture = bpy.data.images.load(str(i))
            elif t == "rough":
                roughnessTexture = bpy.data.images.load(str(i))
                roughnessTexture.colorspace_settings.name = 'Non-Color'
            elif t == "norm":
                normalTexture = bpy.data.images.load(str(i))
                normalTexture.colorspace_settings.name = 'Non-Color'
            elif t == "disp":
                displacementTexture = bpy.data.images.load(str(i))
                
        '''check if texture is loaded
            if not loaded, delete relevant node(s)
            if loaded, place texture in relevant texture node and link relevant nodes'''
        if diffuseTexture != None:
            node_imTexDiffuse.image = diffuseTexture
            links.new(node_imTexDiffuse.outputs[0], node_principled.inputs[0])
            links.new(node_mapping.outputs[0], node_imTexDiffuse.inputs[0])
        else:
            nodes.remove(node_imTexDiffuse)
        if roughnessTexture != None:
            node_imTexRoughness.image = roughnessTexture
            links.new(node_imTexRoughness.outputs[0], node_principled.inputs[7])
            links.new(node_mapping.outputs[0], node_imTexRoughness.inputs[0])
        else:
            nodes.remove(node_imTexRoughness)
        if normalTexture != None:
            node_imTexNormal.image = normalTexture
            links.new(node_imTexNormal.outputs[0], node_normalMap.inputs[1])
            links.new(node_normalMap.outputs[0], node_principled.inputs[20])
            links.new(node_mapping.outputs[0], node_imTexNormal.inputs[0])
        else:
            nodes.remove(node_imTexNormal)
            nodes.remove(node_normalMap)
        if displacementTexture != None:
            node_imTexDisplacement.image = displacementTexture
            links.new(node_imTexDisplacement.outputs[0], node_displacement.inputs[0])
            links.new(node_displacement.outputs[0], node_output.inputs[2])
            links.new(node_mapping.outputs[0], node_imTexDisplacement.inputs[0])
        else:
            nodes.remove(node_imTexDisplacement)
            nodes.remove(node_displacement)
        
        
        return mat


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------ 

class properties(PropertyGroup):
    
    pbr_import_path: StringProperty(
        name = "Import directory",
        description = "Choose a directory to batch import PBR texture sets from.\nFormat your files like this: ChosenDirectory/PBRTextureName/textureFiles",
        default = "",
        maxlen = 1024,
        subtype = 'DIR_PATH'
        )
    
    use_fake_user: BoolProperty(
        name = "Use fake user",
        description = "Use fake user on imported materials",
        default = True
        )


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class OT_ImportPbrTextureSets(Operator):
    bl_label = "Import PBR textures"
    bl_idname = "alt.importpbrtexturesets"
    
    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        
        subdirectories = [x for x in pathlib.Path(tool.pbr_import_path).iterdir() if x.is_dir()]
        for sd in subdirectories:
            filePaths = [x for x in pathlib.Path(sd).iterdir() if x.is_file()]
            mat = createPBR.simple(sd.name, filePaths)
            if tool.use_fake_user == True:
                mat.use_fake_user = True
        
        return{'FINISHED'}

class OT_MarkAllMaterialsAsAssets(Operator):
    bl_label = "Mark all materials as assets"
    bl_idname = "alt.markallmaterialssasassets"
    
    def execute(self, context):
        for mat in bpy.data.materials:
            mat.asset_mark()
        return {'FINISHED'}

class OT_ClearMaterialAssets(Operator):
    bl_label = "Unmark all material assets"
    bl_idname = "alt.clearmaterialassets"
    
    def execute(self, context):
        for mat in bpy.data.materials:
            mat.asset_clear()
        return {'FINISHED'}

class OT_MarkAllMeshesAsAssets(Operator):
    bl_label = "Mark all meshes as assets"
    bl_idname = "alt.markallmeshesasassets"
    
    def execute(self, context):
        for mesh in bpy.data.meshes:
            mesh.asset_mark()
        return {'FINISHED'}

class OT_ClearMeshAssets(Operator):
    bl_label = "Unmark all mesh assets"
    bl_idname = "alt.clearmeshassets"
    
    def execute(self, context):
        for mesh in bpy.data.meshes:
            mesh.asset_clear()
        return {'FINISHED'}

class OT_MarkAllObjectsAsAssets(Operator):
    bl_label = "Mark all objects as assets"
    bl_idname = "alt.markallobjectsasassets"
    
    def execute(self, context):
        for object in bpy.data.objects:
            object.asset_mark()
        return {'FINISHED'}

class OT_ClearObjectAssets(Operator):
    bl_label = "Unmark all object assets"
    bl_idname = "alt.clearobjectassets"
    
    def execute(self, context):
        for object in bpy.data.objects:
            object.asset_clear()
        return {'FINISHED'}

class OT_DeleteAllMaterials(Operator):
    bl_label = "Delete all materials"
    bl_idname = "alt.deleteallmaterials"
    
    def execute(self, context):
        for mat in bpy.data.materials:
            bpy.data.materials.remove(mat)
        return {'FINISHED'}

class OT_testOperator(Operator):
    bl_label = "Debug operator"
    bl_idname = "alt.testoperator"

    def execute(self, context):
        scene = context.scene
        tool = scene.assetlibrarytools
        
        print("pbr_import_path:", tool.pbr_import_path)
        print("pbr_template_enum:", tool.pbr_template_enum)
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_panel(Panel):
    bl_label = "AssetLibraryTools"
    bl_idname = "OBJECT_PT_assetlibrarytools_panel"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    bl_category = "AssetLibraryTools"
    bl_context = "objectmode"   
    
    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        tool = scene.assetlibrarytools
        
        box1 = layout.box()
        box1.label(text="Batch import PBR texture sets as simple materials")
        box1.prop(tool, "pbr_import_path")
        box1.prop(tool, "use_fake_user")
        box1.operator("alt.importpbrtexturesets")
        layout.separator()
        
        box2 = layout.box()
        box2.label(text="Batch mark/clear operations")
        box2.operator("alt.markallmaterialssasassets")
        box2.operator("alt.clearmaterialassets")
        box2.separator()
        box2.operator("alt.markallmeshesasassets")
        box2.operator("alt.clearmeshassets")
        box2.separator()
        box2.operator("alt.markallobjectsasassets")
        box2.operator("alt.clearobjectassets")
        layout.separator()
        
        box3 = layout.box()
        box3.label(text="Some random extra operations")
        box3.operator("alt.testoperator")
        box3.operator("alt.deleteallmaterials")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    properties,
    OT_ImportPbrTextureSets,
    OT_MarkAllMaterialsAsAssets,
    OT_ClearMaterialAssets,
    OT_MarkAllMeshesAsAssets,
    OT_ClearMeshAssets,
    OT_MarkAllObjectsAsAssets,
    OT_ClearObjectAssets,
    OT_DeleteAllMaterials,
    OT_testOperator,
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
