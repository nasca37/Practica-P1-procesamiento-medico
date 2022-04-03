
import numpy as np
import matplotlib.pyplot as plt
import pydicom
from pydicom.fileset import FileSet
import PySimpleGUI as sg
import glob,os
import cv2
from skimage import measure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy import ndimage
from pydicom.pixel_data_handlers.util import apply_modality_lut



# Variables globales
SLICE = 1
MAX_SLIDER = 0
SUBIMAGE = False
SUB_POINT_1 = None
SUB_POINT_2 = None 
SECOND_SIZE = (4,8)
AXIS = 2
THRESHOLD = 0.2

SEGMENTATION = False
MASK = None

INTERCEPT = 0
SLOPE = 0


_VARS = {'fig_agg': False,
         'fig_second':False,
         'pltFig': False}

def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

def from_hu_to_ct(value):
    return (value - INTERCEPT) / SLOPE

def load_dicom_folder(path):
    global SLOPE,INTERCEPT
    if path == None:
        return None
    file_paths = glob.glob(path+"/*.dcm")

    img_data = None
    idx = 0
    slices = []
    for f in file_paths:
        dcm = pydicom.dcmread(f)
        slices.append(dcm)
    slices = sorted(slices,key=lambda s: s.SliceLocation)
    SLOPE = slices[0].RescaleSlope
    INTERCEPT = slices[0].RescaleIntercept
    for s in slices:
        
        
        img = np.flip(s.pixel_array,axis=0)
        if idx != 0:
            img_data[:,:,idx] = img
        else:
            img_data = np.zeros((img.shape[0],img.shape[1],len(file_paths)))
            img_data[:,:,idx] = img
        idx = idx + 1
    return np.flip(img_data,axis=2),slices


def obtain_image_slice(data):
    global AXIS,SLICE
    plano = np.zeros((512,512))
    if SLICE > data.shape[AXIS]:
        SLICE = data.shape[AXIS]-1
    if AXIS == 2:
        
        plano = data[:,:,SLICE-1]
    if AXIS == 1:
        plano = data[:,SLICE-1,:]
    if AXIS == 0:
        plano = data[SLICE-1,:,:]
    return plano


def subimage():
    global current_image
    global SUB_POINT_1
    global SUB_POINT_2
    global SUBIMAGE
    if SUB_POINT_1[0] < SUB_POINT_2[0] and SUB_POINT_1[1] < SUB_POINT_2[1]:
        current_image = current_image[SUB_POINT_1[1]:SUB_POINT_2[1],SUB_POINT_1[0]:SUB_POINT_2[0]]
        print(f"Punto 1: {SUB_POINT_1}   Punto 2: {SUB_POINT_2}        1")
    elif SUB_POINT_1[0] > SUB_POINT_2[0] and SUB_POINT_1[1] < SUB_POINT_2[1]:
        current_image = current_image[SUB_POINT_1[1]:SUB_POINT_2[1],SUB_POINT_2[0]:SUB_POINT_1[0]]
        print(f"Punto 1: {SUB_POINT_1}   Punto 2: {SUB_POINT_2}        2")
    elif SUB_POINT_1[0] < SUB_POINT_2[0] and SUB_POINT_1[1] > SUB_POINT_2[1]:
        print(f"Punto 1: {SUB_POINT_1}   Punto 2: {SUB_POINT_2}        3")
        current_image = current_image[SUB_POINT_2[1]:SUB_POINT_1[1],SUB_POINT_1[0]:SUB_POINT_2[0]]
    elif SUB_POINT_1[0] > SUB_POINT_2[0] and SUB_POINT_1[1] > SUB_POINT_2[1]:
        print(f"Punto 1: {SUB_POINT_1}   Punto 2: {SUB_POINT_2}        4")
        current_image = current_image[SUB_POINT_2[1]:SUB_POINT_1[1],SUB_POINT_2[0]:SUB_POINT_1[0]]

    clean_canvas('fig_second')
    show_canvas_sec(current_image)
    SUBIMAGE = False
    SUB_POINT_1, SUB_POINT_2 = None,None

def get_aspect():
    if AXIS == 2:
        return 1
    else:
        return 0.66/8

def obtain_rgb_mask(m):
    mask = np.zeros((m.shape[0],m.shape[1],3))

    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if m[i][j] == True:
                mask[i][j] = [0,255,0]

    return mask

def show_canvas(img):
    global current_image,MASK

    clean_canvas("fig_agg")
    current_image = img
    fig = plt.figure()
    fig.canvas.mpl_connect('button_press_event', onclick)
    if SEGMENTATION:
        Mask = obtain_image_slice(MASK)
        img = (img - np.min(img)) / (np.max(img) - np.min(img)) * 255
        img = cv2.cvtColor(img.astype(np.uint8),cv2.COLOR_GRAY2RGB)
        Mask = obtain_rgb_mask(Mask) 
        img = algoritmo_pintor(img,Mask,0.25)
        img = img.astype(np.uint8)
        print(np.max(img))

    plt.axis("off")
    plt.imshow(img,cmap=plt.cm.get_cmap("bone"),aspect=get_aspect())
    _VARS['fig_agg'] = draw_figure(window['-CANVAS-'].TKCanvas, fig)

def show_canvas_sec(img):
    clean_canvas('fig_second')
    fig = plt.figure()
    plt.imshow(img,cmap=plt.cm.get_cmap("bone"))
    _VARS['fig_second'] = draw_figure(window['-CANVAS2-'].TKCanvas, fig)

def clean_canvas(key):
    if _VARS[key] != False:
        _VARS[key].get_tk_widget().forget()
    
def apply_windowing(min,max):
    global current_image

    img_max = np.max(current_image)
    img_min = np.min(current_image)
    new_min = from_hu_to_ct(min)
    new_max = from_hu_to_ct(max) 
    
    r = (img_max - img_min) / (new_max-new_min+2) # unit of stretching
    out = np.round(r*(current_image-new_min+1)).astype(current_image.dtype) # stretched values
    
    out[current_image<new_min] = img_min
    out[current_image>new_max] = img_max
    
    current_image = out
    return out

def isocontorno(data,x,y,z):
    threshold = 0.1
    mask = np.zeros(data.shape)
    valor = data[y,x,z]
    print(f"En las coordenadas {x} {y} {z} tenemos el valor {valor}")

    mask = np.ma.masked_inside(data,valor-valor*threshold,np.max(data)).mask*1
    struct = ndimage.generate_binary_structure(3, 1)
    struct2 = ndimage.generate_binary_structure(3, 3)
    erodedMask = ndimage.binary_erosion(mask, structure=struct, iterations=1)
    #print(mask)
    mask_labels = measure.label(erodedMask,background=0,connectivity=1)
    pseudo_final = mask_labels == mask_labels[y,x,z]
    mask_final = ndimage.binary_dilation(pseudo_final, structure=struct2, iterations=1)
    show_canvas_sec(obtain_image_slice(mask_final))
    return (mask_final)

def algoritmo_pintor(imgA,imgB,alpha):

    return imgA * (1 - alpha) + imgB*alpha

def updateAxis(value):
    if value == "X":
        return 0
    if value == "Y":
        return 1
    if value == "Z":
        return 2

def openWindowHeader(slices):
    idx = 0
    if SLICE < len(slices):
        idx = SLICE
    interfaz = [[sg.Text(slices[idx])]]
    col_interfaz = [[sg.Column(interfaz,scrollable=True,vertical_scroll_only=True)]] 
    ventanaheader = sg.Window("Header data",col_interfaz,size=(800,600),modal=True)
    while True:
        event, values = ventanaheader.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break
        
    ventanaheader.close()
sg.theme("BluePurple")


layout1 = [[sg.Text("Seleccionar carpeta" ,size=(8,1)),sg.Input(key="-FOLDER-"),sg.FolderBrowse(),sg.Button("Ir"),
           sg.Text("Windowing"),sg.Input(key="wMin",size=(4,1)),sg.Input(key="wMax",size=(4,1)),sg.Button("Aplicar W"),sg.Button("Header")],]

layout2 = [[sg.Canvas(key='-CANVAS-')],]

sliders= [[sg.T('0',size=(4,1), key='-LEFT-'),
            sg.Slider((0,MAX_SLIDER), key='-SLIDER-', orientation='h', enable_events=True, disable_number_display=True),
            sg.T('0', size=(4,1), key='-RIGHT-'),sg.Button("Cambiar slice"),
            sg.Button("Subimagen"), sg.Button("Reset"), sg.Button("Segmentacion"),sg.Listbox(values=("X","Y","Z"), size=(4, 3), key='Axis', enable_events=True)]]

layout3 = [[ sg.Canvas(key="-CANVAS2-")],]


layout = [
        [sg.Column(layout1, key='-COL1-',element_justification='c')],
        [sg.Column(layout2, visible=True, key='-COL2-'),
        sg.VSeperator(),
        sg.Column(layout3,visible=True, key='-COL3-')],
        [sg.Column(sliders,visible=True,key='sliders'),]
          ]


window = sg.Window("Practica 1",layout,size=(1500,700),resizable=True)

dcm_data = np.zeros((512,512,61))
current_image = np.zeros((512,512))
pixel_len_mm = [5, 1, 1]
slices = None

def onclick(event):
    global SUB_POINT_1,SUB_POINT_2,MASK

    print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
          ('double' if event.dblclick else 'single', event.button,
           event.x, event.y, event.xdata, event.ydata))
    if SUBIMAGE:
        if SUB_POINT_1 == None:
            SUB_POINT_1 = (int(event.xdata),int(event.ydata))
        elif SUB_POINT_2 == None:
            SUB_POINT_2 = (int(event.xdata),int(event.ydata))
            subimage()
    if SEGMENTATION:
        MASK = isocontorno(dcm_data,int(event.xdata),int(event.ydata),SLICE)
        show_canvas(obtain_image_slice(dcm_data))

while True:
    
    event,values = window.read()
    if event in (sg.WIN_CLOSED,"Exit"):
        break
    if event == "Ir":
        dcm_data,slices = load_dicom_folder(values["-FOLDER-"])
        print(f"tamaño slices: {len(slices)}")
        MAX_SLIDER = dcm_data.shape[AXIS]
        slider = window['-SLIDER-']
        slider.Update(range=(0, MAX_SLIDER))
        img = obtain_image_slice(dcm_data)
        show_canvas(img)

    if event == "Cambiar slice":
        SLICE = int(values["-SLIDER-"])
        img = obtain_image_slice(dcm_data)
        show_canvas(img)
        window.refresh()

    if event == "Aplicar W":
 
        data = apply_windowing(float(values['wMin']),float(values['wMax']))
        
        show_canvas_sec(data)
        window.refresh()

    if event == "Subimagen":
        SUBIMAGE = True
    if event == "Reset":
        SEGMENTATION = False
        img = obtain_image_slice(dcm_data)
        show_canvas(img)
        clean_canvas("fig_second")
        window.refresh()
    
    if values["Axis"]:
        AXIS = updateAxis(values["Axis"][0])
        show_canvas(obtain_image_slice(dcm_data))
        MAX_SLIDER = dcm_data.shape[AXIS]
        slider = window['-SLIDER-']
        slider.Update(range=(0, MAX_SLIDER))
    if event == "Segmentacion":
        SEGMENTATION = True
    if event == "Header":
        openWindowHeader(slices)

    window['-LEFT-'].update(int(values['-SLIDER-']))
    window['-RIGHT-'].update(int(MAX_SLIDER))
window.close()

