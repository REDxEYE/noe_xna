import random
import struct
import array
import time

from inc_noesis import *
import rapi
import noesis

noesis.logPopup()

from py_xna_lib import parse_ascii_mesh, parse_ascii_mesh_from_file


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


def load_model(data, mdl_list):
    start_time = time.time()
    data = [line.strip('\n\r') for line in data.decode('utf-8').split('\n') if line]
    fpath = rapi.getInputName()
    fname, root = os.path.basename(fpath), os.path.dirname(fpath)
    skel_path = os.path.join(root, fname[:-6] + '_skel.ascii')
    if os.path.exists(skel_path):
        extenal_skeleton = parse_ascii_mesh_from_file(skel_path)
    else:
        extenal_skeleton = None
    if len(data) < 10:
        print('File is too short')
        return 0
    ctx = rapi.rpgCreateContext()
    model = parse_ascii_mesh(data, extenal_skeleton is not None)

    materials = {}
    textures = []
    specular_texture = NoeTexture('default_spec', 1, 1, b'\x80\x80\x80\x80')
    textures.append(specular_texture)
    for mesh in model.meshes:
        material = mesh.material
        if material:
            mat_name = material.name
            if mat_name in materials:
                continue
            noe_mat = NoeMaterial(mat_name, '')
            noe_mat.flags |= noesis.NMATFLAG_PBR_SPEC
            noe_mat.setFlags2(noe_mat.flags2 | noesis.NMATFLAG2_PREFERPPL)
            noe_mat.setFlags2(noe_mat.flags2 | noesis.NMATFLAG2_VCOLORMATDIFFUSE)
            noe_mat.setRoughness(0.5, -0.3)
            noe_mat.setSpecularTexture('default_spec')
            noe_mat.setNormalTexture(noesis.getScenesPath() + "sample_pbr_n.png")
            noe_mat.setEnvTexture(noesis.getScenesPath() + "sample_pbr_e4.dds")
            has_diffuse = False
            for i, texture in enumerate(material.textures):
                texture_name = os.path.splitext(texture[0])[0]
                noe_tex = rapi.loadExternalTex(texture_name)
                if noe_tex is None:
                    continue
                if i == 0:
                    has_diffuse = True
                    print("Diffuse ", texture_name)
                    noe_mat.setTexture(texture_name)
                elif i == 1:
                    print("Normal ", texture_name)
                    noe_mat.setNormalTexture(texture_name)
                elif i == 2:
                    print("Spec ", texture_name)
                    noe_mat.setSpecularTexture(texture_name)
                textures.append(noe_tex)
            if not has_diffuse:
                noe_mat.setDiffuseColor([random.uniform(.4, 1) for _ in range(3)] + [1.0])
            materials[mat_name] = noe_mat
    noe_meshes = []
    for mesh in model.meshes:
        print('Loading %s mesh...' % mesh.name)
        if mesh.material:
            name = mesh.material.name
        else:
            name = mesh.name
        noe_mesh = NoeMesh(flatten(flip_sub_elements(mesh.indices)), list_to_type(mesh.vertices, NoeVec3),
                           name)
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

    bones = []
    if extenal_skeleton is not None:
        model_bones = extenal_skeleton.bones
    else:
        model_bones = model.bones
    for bone_id, bone in enumerate(model_bones):
        if bone.quat:
            noe_mat = NoeQuat(bone.quat).toMat43(1)
        else:
            noe_mat = NoeMat43()
        noe_mat[3] = NoeVec3(bone.pos)
        noe_bone = NoeBone(bone_id, bone.name, noe_mat, model_bones[bone.parent_id].name, bone.parent_id)
        bones.append(noe_bone)
    mdl = NoeModel(noe_meshes, bones)
    mdl.setModelMaterials(NoeModelMaterials(textures, list(materials.values())))

    mdl_list.append(mdl)
    print("Import took %.2f seconds" % (time.time() - start_time))
    return 1
