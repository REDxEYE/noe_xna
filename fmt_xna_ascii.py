import random
import struct
import os

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


def list_to_bytes(data_list, fmt):
    buffer = b''
    for item in data_list:
        buffer += struct.pack(fmt, *item)
    return buffer


def load_model(data, mdl_list):
    data = data.decode('utf-8').split('\n')
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
    rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, 1)

    materials = []
    textures = []
    for mesh in model.meshes:
        material = mesh.material
        mat_name = material.name
        if mat_name in materials:
            continue
        noe_mat = NoeMaterial(mat_name, material.textures[0][0])
        for tex in material.textures:
            noe_tex = NoeTexture(tex[0], 0, 0, b'')
            textures.append(noe_tex)
        noe_mat.setDiffuseColor([random.uniform(.4, 1) for _ in range(3)] + [1.0])
        materials.append(noe_mat)
    for mesh in model.meshes:
        rapi.rpgSetName(mesh.name)
        rapi.rpgSetMaterial(mesh.material.name)

        rapi.rpgBindPositionBuffer(list_to_bytes(mesh.vertices, '3f'), noesis.RPGEODATA_FLOAT, 12)
        rapi.rpgBindNormalBuffer(list_to_bytes(mesh.normals, '3f'), noesis.RPGEODATA_FLOAT, 12)
        # rapi.rpgBindColorBuffer(list_to_bytes(mesh.vertex_colors, '4f'), noesis.RPGEODATA_FLOAT, 16, 4)
        if mesh.bone_ids:
            rapi.rpgBindBoneIndexBuffer(list_to_bytes(mesh.bone_ids, '4I'), noesis.RPGEODATA_INT, 16, 4)
            rapi.rpgBindBoneWeightBuffer(list_to_bytes(mesh.weights, '4f'), noesis.RPGEODATA_FLOAT, 16, 4)

        for uv_layer_id, uv_data in mesh.uv_layers.items():
            if uv_layer_id == 0:
                rapi.rpgBindUV1Buffer(list_to_bytes(uv_data, '2f'), noesis.RPGEODATA_FLOAT, 8)
            else:
                rapi.rpgBindUVXBuffer(list_to_bytes(uv_data, '2f'), noesis.RPGEODATA_FLOAT, 8, uv_layer_id,
                                      len(uv_data) * 2)

        rapi.rpgCommitTriangles(list_to_bytes(mesh.indices, '3I'), noesis.RPGEODATA_INT, len(mesh.indices) * 3,
                                noesis.RPGEO_TRIANGLE, 1)

        rapi.rpgClearBufferBinds()
        rapi.rpgOptimize()

    mdl = rapi.rpgConstructModel()
    bones = []
    if extenal_skeleton is not None:
        model_bones = extenal_skeleton.bones
    else:
        model_bones = model.bones
    for bone_id, bone in enumerate(model_bones):
        noe_mat = NoeQuat(bone.quat).toMat43(1)
        noe_mat[3] = NoeVec3(bone.pos)
        noe_bone = NoeBone(bone_id, bone.name, noe_mat, model_bones[bone.parent_id].name, bone.parent_id)
        bones.append(noe_bone)
    mdl.setBones(bones)
    mdl.setModelMaterials(NoeModelMaterials(textures, materials))
    mdl_list.append(mdl)
    return 1
