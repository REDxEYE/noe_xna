import random
import time
from inc_noesis import *
import rapi
import noesis

noesis.logPopup()
from py_xna_lib import parse_ascii_mesh, parse_ascii_mesh_from_file, parse_ascii_material_from_file, parse_bone_names, \
    parse_bone_names_from_file


# noinspection PyPep8Naming
def registerNoesisTypes():
    handle = noesis.register("XNA ascii mesh", ".ascii")
    noesis.setHandlerTypeCheck(handle, check_type)
    noesis.setHandlerLoadModel(handle, load_model)
    # noesis.setHandlerWriteModel(handle, noepyWriteModel)
    # noesis.setHandlerWriteAnim(handle, noepyWriteAnim)
    noesis.setTypeSharedModelFlags(handle, noesis.NMSHAREDFL_FLATWEIGHTS)
    noesis.setTypeSharedModelFlags(handle, noesis.NMSHAREDFL_WANTNEIGHBORS)

    return 1


def check_type(data):
    data = data.decode('utf-8').split('\n')
    if len(data) < 10:
        print('File is too short')
        return 0
    return 1


def list_to_type(data_list, type_):
    return [type_(i) for i in data_list]


def flatten(data_list):
    new_list = []
    [new_list.extend(i) for i in data_list]
    return new_list


def flip_sub_elements(data_list):
    for i in range(len(data_list)):
        data_list[i] = data_list[i][::-1]
    return data_list


def fill_up_to(data_list, elen, filler=1.0):
    for i in range(len(data_list)):
        len1 = len(data_list[i])
        if len1 < elen:
            data_list[i] = tuple(data_list[i]) + tuple([filler] * (elen - len1))
    return data_list


def get_neighbor_file(old_path, new_name):
    root = os.path.dirname(old_path)
    return os.path.join(root, new_name)


def load_model(data, mdl_list):
    start_time = time.time()
    data = [line.strip('\n\r') for line in data.decode('utf-8').split('\n') if line]
    original_file_path = rapi.getInputName()
    file_name = os.path.basename(original_file_path)

    bone_remap_file = get_neighbor_file(original_file_path, 'bonenames.txt')
    ascii_skel_path = get_neighbor_file(original_file_path, file_name[:-6] + '_skel.ascii')
    # smd_skel_path = get_neighbor_file(original_file_path, file_name[:-6] + '_skel.smd')
    if os.path.exists(bone_remap_file):
        print('Using bone names remap file "%s"' % bone_remap_file)
        remap_table = parse_bone_names_from_file(bone_remap_file)
    else:
        remap_table = None
    if os.path.exists(ascii_skel_path):
        print('Using external ASCII skeleton "%s"' % ascii_skel_path)
        external_skeleton = parse_ascii_mesh_from_file(ascii_skel_path)
        external_bones = external_skeleton.bones
    # elif os.path.exists(smd_skel_path):
    #     print('Using external SMD skeleton "%s"' % smd_skel_path)
    #     external_bones = parse_smd_bones_from_file(smd_skel_path)
    else:
        external_bones = None
    if len(data) < 10:
        print('File is too short')
        return 0
    model = parse_ascii_mesh(data, external_bones is not None)
    print('Statistic for "%s" file:' % original_file_path)
    for mesh in model.meshes:
        print('  Mesh "%s":' % mesh.name)
        print('    Triangles: %i' % len(mesh.indices))
        print('    Vertices: %i' % len(mesh.vertices))
        print('    UV layers: %i' % len(mesh.uv_layers))
        print('    Weights: %s' % str(len(mesh.weights) > 0))

    materials = {}
    textures = {}
    for mesh in model.meshes:
        material = mesh.material
        if material:
            mat_name = material.name
            if mat_name in materials:
                continue
            print('Loading material %s' % mat_name)
            noe_mat = NoeMaterial(mat_name, '')
            noe_mat.setFlags2(noe_mat.flags2 | noesis.NMATFLAG2_PREFERPPL)
            noe_mat.setFlags2(noe_mat.flags2 | noesis.NMATFLAG2_VCOLORMATDIFFUSE)
            noe_mat.setRoughness(0.5, -0.3)

            amat_path = get_neighbor_file(original_file_path, mat_name + '.amat')
            if os.path.exists(amat_path):
                print('Using AMAT "%s"' % amat_path)
                amat_material = parse_ascii_material_from_file(amat_path)
            else:
                print('Using built-in material')
                amat_material = mesh.material

            if 'Diffuse' in amat_material.textures:
                texture, _ = amat_material.textures['Diffuse']
                print('Setting Diffuse texture to %s' % texture)
                noe_mat.setTexture(texture)
                if load_texture(original_file_path, texture, textures) is None:
                    noe_mat.setDiffuseColor([random.uniform(.4, 1) for _ in range(3)] + [1.0])

            if 'Normal' in amat_material.textures:
                texture, _ = amat_material.textures['Normal']
                print('Setting Normal texture to %s' % texture)
                noe_mat.setNormalTexture(texture)
                load_texture(original_file_path, texture, textures)
            if 'Specular' in amat_material.textures:
                texture, _ = amat_material.textures['Specular']
                print('Setting Specular texture to %s' % texture)
                noe_mat.setSpecularTexture(texture)
                load_texture(original_file_path, texture, textures)

            materials[mat_name] = noe_mat
        else:
            if mesh.name in materials:
                continue
            noe_mat = NoeMaterial(mesh.name, '')
            noe_mat.setDiffuseColor([random.uniform(.4, 1) for _ in range(3)] + [1.0])
            materials[mesh.name] = noe_mat
    noe_meshes = []
    for mesh in model.meshes:
        print('Loading %s mesh...' % mesh.name)
        name = mesh.name
        noe_mesh = NoeMesh(flatten(flip_sub_elements(mesh.indices)), list_to_type(mesh.vertices, NoeVec3), name)
        noe_mesh.setMaterial(name)
        noe_mesh.setNormals(list_to_type(mesh.normals, NoeVec3))
        noe_mesh.setColors(list_to_type(mesh.vertex_colors, NoeVec4))
        for uv_layer_id, uv_data in mesh.uv_layers.items():
            noe_mesh.setUVs(list_to_type(fill_up_to(uv_data, 3, 0), NoeVec3), uv_layer_id + uv_layer_id != 0)
        if mesh.bone_ids:
            weights = [NoeVertWeight(bone_ids, bone_weights)
                       for bone_ids, bone_weights in zip(mesh.bone_ids, mesh.weights)]
            noe_mesh.setWeights(weights)
        noe_meshes.append(noe_mesh)

    if external_bones is not None:
        model_bones = external_bones
    else:
        model_bones = model.bones

    for bone in model_bones:
        if remap_table is not None:
            bone.name = remap_table.get(bone.name, bone.name)

    bones = []
    for bone_id, bone in enumerate(model_bones):
        bone_name = bone.name
        if 'unused' in bone_name:
            continue

        if bone.quat:
            noe_mat = NoeQuat(bone.quat).toMat43(1)
        else:
            noe_mat = NoeMat43()
        noe_mat[3] = NoeVec3(bone.pos)

        noe_bone = NoeBone(bone_id, bone_name, noe_mat,
                           model_bones[bone.parent_id].name if bone.parent_id != -1 else None)
        bones.append(noe_bone)
    mdl = NoeModel(noe_meshes, bones)
    mdl.setModelMaterials(NoeModelMaterials(list(textures.values()), list(materials.values())))
    mdl_list.append(mdl)

    print("Import took %.2f seconds" % (time.time() - start_time))
    return 1


def load_texture(original_file_path, texture, textures):
    if texture in textures:
        return textures[texture]
    full_texture_path = get_neighbor_file(original_file_path, texture)
    print('Loading texture from %s' % full_texture_path)
    noe_texture = rapi.loadExternalTex(full_texture_path)
    if noe_texture is None:
        full_texture_path = get_neighbor_file(os.path.join(original_file_path, 'textures'), texture)
        print('Loading texture from %s' % full_texture_path)
        noe_texture = rapi.loadExternalTex(full_texture_path)
        if noe_texture is None:
            return None

    noe_texture.name = texture
    textures[noe_texture.name] = noe_texture
    return noe_texture
