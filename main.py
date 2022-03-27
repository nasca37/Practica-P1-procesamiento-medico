
import numpy as np
import matplotlib.pyplot as plt
import pydicom
from pydicom.fileset import FileSet
import PySimpleGUI as sg
import glob,os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

SLICE = 1
MAX_SLIDER = 0
SUBIMAGE = False
SUB_POINT_1 = None
SUB_POINT_2 = None 
SECOND_SIZE = (4,8)

_VARS = {'fig_agg': False,
         'fig_second':False,
         'pltFig': False}

def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def load_dicom_folder(path):
    if path == None:
        return None
    file_paths = glob.glob(path+"/*.dcm")

    img_data = None
    idx = 0
    for f in file_paths:
        dcm = pydicom.dcmread(f)
        img = np.flip(dcm.pixel_array,axis=0)

        if idx != 0:
            img_data[:,:,idx] = img
        else:
            img_data = np.zeros((img.shape[0],img.shape[1],len(file_paths)))
            img_data[:,:,idx] = img
        idx = idx + 1
    return img_data


def obtain_image_slice(data):
    plano = data[:,:,SLICE]
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

def show_canvas(img):
    global current_image

    current_image = img
    fig = plt.figure()
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.imshow(img,cmap=plt.cm.get_cmap("bone"))
    _VARS['fig_agg'] = draw_figure(window['-CANVAS-'].TKCanvas, fig)

def show_canvas_sec(img):
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
    new_min = img_max * min
    new_max = img_max * max
    r = np.max(current_image)/(new_max-new_min+2) # unit of stretching
    out = np.round(r*(current_image-new_min+1)).astype(current_image.dtype) # stretched values
    out[current_image<new_min] = img_min
    out[current_image>new_max] = img_max
    current_image = out
    return out



sg.theme("BluePurple")

layout1 = [[sg.Text("Seleccionar carpeta" ,size=(8,1)),sg.Input(key="-FOLDER-"),sg.FolderBrowse(),sg.Button("Ir"),
           sg.Text("Windowing"),sg.Input(key="wMin",size=(4,1)),sg.Input(key="wMax",size=(4,1)),sg.Button("Aplicar W")],]

layout2 = [[sg.Canvas(key='-CANVAS-')],]

sliders= [[sg.T('0',size=(4,1), key='-LEFT-'),
            sg.Slider((0,MAX_SLIDER), key='-SLIDER-', orientation='h', enable_events=True, disable_number_display=True),
            sg.T('0', size=(4,1), key='-RIGHT-'),sg.Button("Cambiar slice"),
            sg.Button("Subimagen"), sg.Button("Reset")],]

layout3 = [[sg.Text("Panel secundario"), sg.Canvas(key="-CANVAS2-")],]


layout = [
        [sg.Column(layout1, key='-COL1-',element_justification='c')],
        [sg.Column(layout2, visible=True, key='-COL2-'),
        sg.VSeperator(),
        sg.Column(layout3,visible=True, key='-COL3-')],
        [sg.Column(sliders,visible=True,key='sliders'),]
          ]


window = sg.Window("Practica 1",layout,size=(1600,800),resizable=True)

dcm_data = np.zeros((512,512,61))
current_image = np.zeros((512,512))
pixel_len_mm = [5, 1, 1]

def onclick(event):
    global SUB_POINT_1
    global SUB_POINT_2
    print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
          ('double' if event.dblclick else 'single', event.button,
           event.x, event.y, event.xdata, event.ydata))
    if SUBIMAGE:
        if SUB_POINT_1 == None:
            SUB_POINT_1 = (int(event.xdata),int(event.ydata))
        elif SUB_POINT_2 == None:
            SUB_POINT_2 = (int(event.xdata),int(event.ydata))
            subimage()
            

while True:
    event,values = window.read()
    if event in (sg.WIN_CLOSED,"Exit"):
        break
    if event == "Ir":
        dcm_data = load_dicom_folder(values["-FOLDER-"])

        MAX_SLIDER = dcm_data.shape[2]
        slider = window['-SLIDER-']
        slider.Update(range=(0, MAX_SLIDER))

        img = obtain_image_slice(dcm_data)
        clean_canvas("fig_agg")
        clean_canvas("fig_second")
        show_canvas(img)

    if event == "Cambiar slice":
        SLICE = int(values["-SLIDER-"])
        clean_canvas('fig_agg')
        img = obtain_image_slice(dcm_data)
        show_canvas(img)
        window.refresh()

    if event == "Aplicar W":
 
        data = apply_windowing(float(values['wMin']),float(values['wMax']))
        clean_canvas('fig_second')
        show_canvas_sec(data)
        window.refresh()

    if event == "Subimagen":
        SUBIMAGE = True
    if event == "Reset":
        img = obtain_image_slice(dcm_data)
        show_canvas(img)
        clean_canvas('fig_second')
        clean_canvas('fig_agg')
        window.refresh()

    window['-LEFT-'].update(int(values['-SLIDER-']))
    window['-RIGHT-'].update(int(MAX_SLIDER))
window.close()

