
from ast import If
import bmesh
import requests
import os
import cv2
import numpy as np
import webbrowser
import bpy

CLIENT_ID = "56651af3c4134034b9977c0a650b2cdf"
CLIENT_SECRET = "ba05f9e81dbc4443857aa9f3afcfc88b"
REDIRECT_URL = "http://127.0.0.1:5555/callback.html"
# DO NOT PUSH WHEN USER_CODE IS NOT ""!!!
USER_CODE = ""

AUTH_URL = "https://accounts.spotify.com/api/token"
CLIENT_AUTH_URL = "https://accounts.spotify.com/authorize"
BASE_URL = "https://api.spotify.com/v1/"


PLANE_AMOUNT = 100
COLOR_DIFFERECE = 0.1
materials = []
material_index = []

# get access token
auth_response = requests.post(AUTH_URL, {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})
auth_response_data = auth_response.json()
access_token = auth_response_data['access_token']

headers = {
    'Authorization': 'Bearer {token}'.format(token=access_token)
}

# Opens login screen -> After redirect, you can see the users code. (Live Server must be active!)


def requestAuthorization():
    url = CLIENT_AUTH_URL
    url += "?client_id=" + CLIENT_ID
    url += "&response_type=code"
    url += "&redirect_uri=" + REDIRECT_URL
    url += "&show_dialog=true"
    url += "&scope=user-read-private user-read-email user-modify-playback-state user-read-playback-position user-library-read streaming user-read-playback-state user-read-recently-played playlist-read-private"
    webbrowser.open(url, new=0, autoraise=True)

# Gets song from track id


def getSong(track_id):
    r = requests.get(BASE_URL + "tracks/" + track_id, headers=headers)
    d = r.json()

    artist = d["artists"][0]["name"]
    track = d["name"]
    print("--- Chosen Track ---")
    print(artist, "-", track)
    print()

# Gets cover from song


def getSongImage(track_id):
    getSong(track_id)
    r = requests.get(BASE_URL + "tracks/" + track_id, headers=headers)
    d = r.json()

    # Get image part
    cover_image = requests.get(d["album"]["images"][0]['url'])
    img_string = np.frombuffer(cover_image.content, np.uint8)
    img = cv2.imdecode(img_string, cv2.IMREAD_COLOR)
    createCoverFromImage(img)

    # Show pixeled cover image
    resized = cv2.resize(img, (100, 100), interpolation=cv2.INTER_NEAREST)
    cv2.namedWindow('img', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('img', 500, 500)
    cv2.imshow('img', resized)
    cv2.waitKey(0)

# Get image part end

# Gets all albums from artist


def getArtistsAlbums(artist_id):

    r = requests.get(BASE_URL + "artists/" + artist_id,
                     headers=headers)
    a = r.json()

    print("--- All Albums by the Artist '" + a["name"] + "' ---")

    r = requests.get(BASE_URL + "artists/" + artist_id + "/albums",
                     headers=headers,
                     params={"include_groups": "album", "limit": 50})
    d = r.json()

    albums = []
    for album in d["items"]:
        album_name = album["name"]

        trim_name = album_name.split('(')[0].strip()  # Filter out duplicates
        if trim_name.upper() in albums:
            continue

        albums.append(trim_name.upper())

        print(album_name, "---", album["release_date"])

    print()


def createCoverFromImage(img):
    global PLANE_AMOUNT
    global materials
    global material_index
    # Select all objects
    bpy.ops.object.select_all(action='SELECT')
    # Delete the selected Objects
    bpy.ops.object.delete(use_global=False, confirm=False)
    # Delete mesh-data
    bpy.ops.outliner.orphans_purge()
    # Delete materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)
    verts = []

    cover_mesh = bpy.data.meshes.new("cover mesh")
    cover_object = bpy.data.objects.new("cover", cover_mesh)
    bpy.context.collection.objects.link(cover_object)
    bm = bmesh.new()
    bm.from_mesh(cover_mesh)
    # Create Material
    rows, cols, _ = img.shape
    for i in range(PLANE_AMOUNT):
        for j in range(PLANE_AMOUNT):
            """ new_mat = bpy.data.materials.new(
                'mat_' + str(i) + "_" + str(j))
            color = img[int(i*rows/PLANE_AMOUNT), int(j*cols/PLANE_AMOUNT)]
            new_mat.diffuse_color = (
                (color[2]/255, color[1]/255, color[0]/255, 1)) """
            createMaterial(
                img[int(i*rows/PLANE_AMOUNT), int(j*cols/PLANE_AMOUNT)])
    for i in range(len(materials)):
         cover_object.data.materials.append(materials[i])            
    #  Creating the verts
    for x in range(PLANE_AMOUNT + 1):
        verts.append([])
        for y in range(PLANE_AMOUNT + 1):
            new_vert = bm.verts.new(
                (0, int(y - PLANE_AMOUNT/2), -int(x-PLANE_AMOUNT/2)))
            verts[x].append(new_vert)
    # Connect 4 verts to a face and append to faces array
    bm.verts.ensure_lookup_table()
    face_counter = 0
    for x in range(len(verts)-1):
        for y in range(len(verts[x])-1):
            new_face = bm.faces.new(
                (verts[x][y], verts[x][y+1], verts[x+1][y+1], verts[x+1][y]))
            new_face.material_index = material_index[face_counter]
            face_counter += 1

    bm.to_mesh(cover_mesh)
    bm.free()


def createMaterial(color):
    global materials
    global material_index

    new_color = (round(color[2]/255, 1),
                 round(color[1]/255, 1), 
                 round(color[0]/255, 1), 
                 1) 
    index = material_is_already_available(new_color)
    if(index == -1):
        new_mat = bpy.data.materials.new(
            'mat_' + str(len(materials)))
        new_mat.diffuse_color = new_color
        material_index.append(len(materials))
        materials.append(new_mat)
    else: 
        material_index.append(index)

def material_is_already_available(color):
    global materials
    global COLOR_DIFFERECE
    for i in range(len(materials)):
        if (materials[i].diffuse_color[0] + COLOR_DIFFERECE > color[0] and materials[i].diffuse_color[0] - COLOR_DIFFERECE < color[0]):
            if (materials[i].diffuse_color[1] + COLOR_DIFFERECE > color[1] and materials[i].diffuse_color[1] - COLOR_DIFFERECE < color[1]):
                if(materials[i].diffuse_color[2] + COLOR_DIFFERECE > color[2] and materials[i].diffuse_color[2] - COLOR_DIFFERECE < color[2]):
                    return i
    return -1


def clear():
    os.system('cls')


if (__name__ == "__main__"):
    clear()
    # requestAuthorization()
    # getSong("3I2Jrz7wTJTVZ9fZ6V3rQx")
    # getArtistsAlbums("26T3LtbuGT1Fu9m0eRq5X3")
    getSongImage("3I2Jrz7wTJTVZ9fZ6V3rQx")
