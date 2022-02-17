import random
import struct
import array

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
    ar = array.array(fmt, [])
    for item in data_list:
        ar.extend(item)
    return ar.tobytes()


def load_model(data, mdl_list):
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
    rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, 1)

    materials = {}
    textures = []
    specular_texture = NoeTexture('default_spec', 1, 1, b'\x80\x80\x80\x80')
    textures.append(specular_texture)
    for mesh in model.meshes:
        material = mesh.material
        mat_name = material.name
        if mat_name in materials:
            continue
        noe_mat = NoeMaterial(mat_name, '')
        noe_mat.flags |= noesis.NMATFLAG_PBR_SPEC
        noe_mat.setFlags2(noe_mat.flags2 | noesis.NMATFLAG2_PREFERPPL)
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
    for mesh in model.meshes:
        print('Loading %s mesh...' % mesh.name)
        rapi.rpgSetName(mesh.name)
        rapi.rpgSetMaterial(mesh.material.name)

        rapi.rpgBindPositionBuffer(list_to_bytes(mesh.vertices, 'f'), noesis.RPGEODATA_FLOAT, 12)
        rapi.rpgBindNormalBuffer(list_to_bytes(mesh.normals, 'f'), noesis.RPGEODATA_FLOAT, 12)
        # rapi.rpgBindColorBuffer(list_to_bytes(mesh.vertex_colors, '4f'), noesis.RPGEODATA_FLOAT, 16, 4)
        if mesh.bone_ids:
            bone_per_vertex = len(mesh.bone_ids[0])
            rapi.rpgBindBoneIndexBuffer(list_to_bytes(mesh.bone_ids, 'I'), noesis.RPGEODATA_INT, 16,
                                        bone_per_vertex)
            rapi.rpgBindBoneWeightBuffer(list_to_bytes(mesh.weights, 'f'), noesis.RPGEODATA_FLOAT,
                                         16, bone_per_vertex)

        for uv_layer_id, uv_data in mesh.uv_layers.items():
            if uv_layer_id == 0:
                rapi.rpgBindUV1Buffer(list_to_bytes(uv_data, 'f'), noesis.RPGEODATA_FLOAT, 8)
            else:
                rapi.rpgBindUVXBuffer(list_to_bytes(uv_data, 'f'), noesis.RPGEODATA_FLOAT, 8, uv_layer_id,
                                      len(uv_data) * 2)

        rapi.rpgCommitTriangles(list_to_bytes(mesh.indices, 'I'), noesis.RPGEODATA_INT, len(mesh.indices) * 3,
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
        if bone.quat:
            noe_mat = NoeQuat(bone.quat).toMat43(1)
        else:
            noe_mat = NoeMat43()
        noe_mat[3] = NoeVec3(bone.pos)
        noe_bone = NoeBone(bone_id, bone.name, noe_mat, model_bones[bone.parent_id].name, bone.parent_id)
        bones.append(noe_bone)
    mdl.setBones(bones)
    mdl.setModelMaterials(NoeModelMaterials(textures, list(materials.values())))
    mdl_list.append(mdl)
    return 1
