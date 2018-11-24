from ctypes import Structure, c_int, POINTER, WINFUNCTYPE, windll, WinError, sizeof
from ctypes.wintypes import BOOL, HWND, RECT, HDC, HBITMAP, HGDIOBJ, DWORD, LONG, WORD, UINT, LPVOID
import numpy as np
import ctypes
import cv2
import os


SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0

LONG = ctypes.c_long
DWORD = ctypes.c_ulong
ULONG_PTR = ctypes.POINTER(DWORD)
WORD = ctypes.c_ushort
VK_DOWN = 0x28
VK_UP = 0x26
KEYEVENTF_KEYUP = 0x0002
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
hell = True
global threshold_value
threshold_value=200




"""defined global variables"""
drag=[]
roi_co_ordinates=[(95, 153), (637, 328)]#(57, 151), (526, 362)
RegionSelected = False
frames=[]
pressedlast=[0]*2
timeForVelocity=[0]*2
fourcc=cv2.VideoWriter_fourcc(*'XVID')
out=cv2.VideoWriter('frames.avi',fourcc,10.0,(637-95,328-153))


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (('wVk', WORD),
                ('wScan', WORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))
class MOUSEINPUT(ctypes.Structure):
    _fields_ = (('dx', LONG),
                ('dy', LONG),
                ('mouseData', DWORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))

class _INPUTunion(ctypes.Union):
    _fields_ = (('ki', KEYBDINPUT),
                ('mi', MOUSEINPUT))

class INPUT(ctypes.Structure):
    _fields_ = (('type', DWORD),
                ('union', _INPUTunion))


def Keyboard(code, flags=0):
    return Input(KeybdInput(code, flags))


def KeybdInput(code, flags):
    return KEYBDINPUT(code, code, flags, 0, None)

def Input(structure):
    if isinstance(structure, MOUSEINPUT):
        return INPUT(INPUT_MOUSE, _INPUTunion(mi=structure))
    if isinstance(structure, KEYBDINPUT):
        return INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure))
    raise TypeError('Cannot create INPUT structure!')


def SendInput(*inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.c_int(ctypes.sizeof(INPUT))
    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

def press_up():
    SendInput(Keyboard(VK_UP))
    cv2.waitKey(2)
    SendInput(Keyboard(VK_UP,KEYEVENTF_KEYUP))


def press_down():
    SendInput(Keyboard(VK_DOWN))

def release_down():
    SendInput(Keyboard(VK_DOWN,KEYEVENTF_KEYUP))




class BITMAPINFOHEADER(Structure):
    _fields_ = [('biSize', DWORD),
                ('biWidth', LONG),
                ('biHeight', LONG),
                ('biPlanes', WORD),
                ('biBitCount', WORD),
                ('biCompression', DWORD),
                ('biSizeImage', DWORD),
                ('biXPelsPerMeter', LONG),
                ('biYPelsPerMeter', LONG),
                ('biClrUsed', DWORD),
                ('biClrImportant', DWORD)]


def err_on_zero_or_null_check(result, func, args):
    if not result:
        raise WinError()
    return args


def quick_win_define(name, output, *args, **kwargs):
    dllname, fname = name.split('.')
    params = kwargs.get('params', None)
    if params:
        params = tuple([(x, ) for x in params])
    func = (WINFUNCTYPE(output, *args))((fname, getattr(windll, dllname)), params)
    err = kwargs.get('err', err_on_zero_or_null_check)
    if err:
        func.errcheck = err
    return func


GetClientRect = quick_win_define('user32.GetClientRect', BOOL, HWND, POINTER(RECT), params=(1, 2))
GetDC = quick_win_define('user32.GetDC', HDC, HWND)
CreateCompatibleDC = quick_win_define('gdi32.CreateCompatibleDC', HDC, HDC)
CreateCompatibleBitmap = quick_win_define('gdi32.CreateCompatibleBitmap', HBITMAP, HDC, c_int, c_int)
ReleaseDC = quick_win_define('user32.ReleaseDC', c_int, HWND, HDC)
DeleteDC = quick_win_define('gdi32.DeleteDC', BOOL, HDC)
DeleteObject = quick_win_define('gdi32.DeleteObject', BOOL, HGDIOBJ)
SelectObject = quick_win_define('gdi32.SelectObject', HGDIOBJ, HDC, HGDIOBJ)
BitBlt = quick_win_define('gdi32.BitBlt', BOOL, HDC, c_int, c_int, c_int, c_int, HDC, c_int, c_int, DWORD)
GetDIBits = quick_win_define('gdi32.GetDIBits', c_int, HDC, HBITMAP, UINT, UINT, LPVOID, POINTER(BITMAPINFOHEADER), UINT)
GetDesktopWindow = quick_win_define('user32.GetDesktopWindow', HWND)


class Grabber(object):
    def __init__(self, window=None, with_alpha=False, bbox=None):
        window = window or GetDesktopWindow()
        self.window = window
        rect = GetClientRect(window)
        print (rect)
        self.width = rect.right - rect.left
        self.height = rect.bottom - rect.top
        if bbox:
            bbox = [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]]
            if not bbox[2] or not bbox[3]:
                bbox[2] = self.width - bbox[0]
                bbox[3] = self.height - bbox[1]
            self.x, self.y, self.width, self.height = bbox
        else:
            self.x = 0
            self.y = 0
        self.windowDC = GetDC(window)
        self.memoryDC = CreateCompatibleDC(self.windowDC)
        self.bitmap = CreateCompatibleBitmap(self.windowDC, self.width, self.height)
        self.bitmapInfo = BITMAPINFOHEADER()
        self.bitmapInfo.biSize = sizeof(BITMAPINFOHEADER)
        self.bitmapInfo.biPlanes = 1
        self.bitmapInfo.biBitCount = 32 if with_alpha else 24
        self.bitmapInfo.biWidth = self.width
        self.bitmapInfo.biHeight = -self.height
        self.bitmapInfo.biCompression = BI_RGB
        self.bitmapInfo.biSizeImage = 0
        self.channels = 4 if with_alpha else 3
        self.closed = False

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def close(self):
        if self.closed:
            return
        ReleaseDC(self.window, self.windowDC)
        DeleteDC(self.memoryDC)
        DeleteObject(self.bitmap)
        self.closed = True

    def grab(self, output=None):
        if self.closed:
            raise ValueError('solti  closed')
        if output is None:
            output = np.empty((self.height, self.width, 3), dtype='uint8')
        else:
            if output.shape != (self.height, self.width, 3):
                raise ValueError('milena solti')
        SelectObject(self.memoryDC, self.bitmap)
        BitBlt(self.memoryDC, 0, 0, self.width, self.height, self.windowDC, 0, 0, SRCCOPY)
        GetDIBits(self.memoryDC, self.bitmap, 0, self.height, output.ctypes.data, self.bitmapInfo,
                      DIB_RGB_COLORS)

        return output













def find_roi(event,x,y,flags,param):
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_co_ordinates.append((x,y))
    elif event == cv2.EVENT_LBUTTONUP:
        roi_co_ordinates.append((x, y))

def image_processing(mainImg,col,minDist,col1):
    global threshold_value
    loop=False
    global previousContours
    global frameCount
    global black_thres
    areas=[]
    centerList=[]
    radiusList=[]
    moments=[]
    centroid=[]
    neededCentros=[]
    filteredRadius=[]
    skip=True
    if col<=246:
        out.write(mainImg)
        if col!=col1:
            b,g,r=cv2.split(mainImg)
            b=255-b
            mainImg=cv2.merge((b,b,b))
            threshold_value=255-col1+10



    else:
        threshold_value=195

    cont=0
    cv2.GaussianBlur(mainImg, (5, 5), 0, mainImg, 0)
    cv2.GaussianBlur(mainImg, (5, 5), 0, mainImg, 0)
    cv2.GaussianBlur(mainImg, (3, 3), 0, mainImg, 0)
    gray_img = cv2.cvtColor(mainImg, cv2.COLOR_BGR2GRAY)
    if skip:
        ret, thres = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
    cv2.imshow("threshold", thres)
    morph = thres.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cv2.erode(morph, kernel, morph, None, 2)
    cv2.dilate(morph, kernel, morph, None, 3)
    cv2.dilate(morph, kernel, morph, None, 3)
    cv2.erode(morph, kernel, morph, None, 2)
    (a, contours, hie) = cv2.findContours(morph, 1, 2)

    if len(contours) > 6:
        print("shit")
    for c in contours:
        (x1, y1), radius = cv2.minEnclosingCircle(c)
        center = (int(x1), int(y1))
        radius = int(radius)
        d = cv2.contourArea(c)
        if d > 5000 or d < 100:
            continue
        M = cv2.moments(c)
        if len(drag) == 0 and len(contours) <= 4:
            drag.append((int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])))
            drag.append(d)
            print("RADIUS for dragon",radius)
        else:
            if len(drag)<2:
                print("what the hell just happened")
                exit()
        areas.append(d)
        radiusList.append(radius)
        centerList.append(center)
        moments.append(M)
        centroid.append((int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])))
        cv2.circle(mainImg, center, radius, (255, 128, 34), 2)
        cv2.imshow("gray", mainImg)

    for c in range(len(centroid)):
            cent = centroid[c]
            area = areas[c]
            rad1 = radiusList[c]
            if (abs(cent[0] - drag[0][0]) < 7) and (abs(area - drag[1]) < 100):
                dIN = c
                cnt = "drago:-(%d,%d)" % (cent[0], cent[1])
                cv2.putText(mainImg, cnt, cent, cv2.FONT_HERSHEY_COMPLEX, 1, (25, 87, 15), 2)
            elif cent[0] < drag[0][0]:
                cnt = "ignored"
                cv2.putText(mainImg, cnt, (cent[0] + 100, cent[1]), cv2.FONT_HERSHEY_COMPLEX, 1, (25, 87, 15), 2)
                continue
            else:
                cnt = ".(%d)." % (rad1)
                cv2.putText(mainImg, cnt, (cent[0] + 50, cent[1]), cv2.FONT_HERSHEY_COMPLEX, 1, (25, 87, 15), 2)
            neededCentros.append(centroid[c])
            filteredRadius.append(rad1)
    finalCentros=sorted(neededCentros)
    neededRadius=filteredRadius
    cv2.imshow("gray", mainImg)
    #print(len(neededCentros))
    for c in range(len(neededCentros)):
            neededRadius[finalCentros.index(neededCentros[c])]=filteredRadius[finalCentros.index(neededCentros[c])]
            #sorting the radius as the sorted value of centroid, (if mistake vayo vane use area for reference instead
            #could make error if chara aayo vane
    if(len(neededCentros)<2):
        print("returned")
        return
    '''if True:
        timeForVelocity[0]=timeForVelocity[1]
        timeForVelocity[1]=time.time()
        pressedlast[0]=pressedlast[1]
        pressedlast[1]=finalCentros[1][0]
        if pressedlast[0]!=0 and timeForVelocity[0]!=0:
            displacement=pressedlast[0]-pressedlast[1]
            tim=timeForVelocity[1]-timeForVelocity[0]
            vel=displacement/tim
            print("displcement value per frame:-",vel)
            if vel<40:
                minDist=118
            elif vel>40 and vel<60:
                minDist=120
            elif vel>60:
                minDist=180
            else:
                minDist=70'''
    previousContours=len(contours)
    threshold_valu=col1
   # print((finalCentros[1][0] + neededRadius[2]) - finalCentros[0][0])
    if (finalCentros[1][0]-neededRadius[1] -finalCentros[0][0]) <minDist:
        if finalCentros[0][1]-finalCentros[1][1]>40:
            print (finalCentros[0][1]-finalCentros[1][1])
            press_down()
            return True

        else:
            press_up()
            return False







def do_nothing_function(c=None):
    pass

def get_threshold(img4):
    cv2.destroyWindow("binary_value")
    return 150
    dup=img4.copy()
    cv2.GaussianBlur(dup, (5, 5), 0, dup, 0)
    cv2.GaussianBlur(dup, (5, 5), 0, dup, 0)
    cv2.GaussianBlur(dup, (3, 3), 0, dup, 0)
    gray_img = cv2.cvtColor(dup, cv2.COLOR_BGR2GRAY)
    value=cv2.getTrackbarPos("THRESHOLD VALUE","binary_value")
    ret, thres = cv2.threshold(gray_img, value,255 , cv2.THRESH_BINARY)
    cv2.imshow("binary_value", thres)
    morph=thres.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cv2.erode(morph, kernel, morph, None,3)
    cv2.dilate(morph, kernel, morph, None, 3)
    cv2.dilate(morph, kernel, morph, None, 3)
    cv2.erode(morph, kernel, morph, None, 2)
    cv2.imshow("morph",morph)
    jkl=cv2.waitKey(35) & 0xff
    if jkl&0xff==101 or jkl&0xff==69:
        cv2.destroyAllWindows()
        return value
    return None








if __name__ == "__main__":
    import cv2
    import time
    threshold_value=190
    black=False
    itr=0
    distCount=0
    minDist=90

    #cv2.namedWindow("Main Window")
    #cv2.namedWindow("ROI")
    img= Grabber(bbox=(0,0,1920, 1080))
    first = True

    if False:  #first
            print("")
            key = 'y'
            if key == 'y' or key == 'Y':
                    output = img.grab()
                    cv2.namedWindow("select_roi")
                    cv2.imshow("select_roi", output)
                    cv2.setMouseCallback("select_roi", find_roi)
                    while True:
                        if len(roi_co_ordinates) <2:
                            cv2.waitKey(30)
                            continue
                        print(roi_co_ordinates)
                        if roi_co_ordinates[0][0] == roi_co_ordinates[1][0] or roi_co_ordinates[0][1] == roi_co_ordinates[1][1]:
                            print("invalid selection try again")
                            roi_co_ordinates.clear()
                            cv2.waitKey(30)
                            continue
                        # have method to write coordinates to file
                        cv2.destroyWindow("select_roi")
                        break
                        print("breaked??")
    if True: #true
            # have method to read from file
            print("do you want to recompute threshold value??")
            key='y'
            if key == 'y' or key == 'Y':
                cv2.namedWindow("binary_value")
                cv2.createTrackbar("THRESHOLD VALUE", "binary_value", 0, 255, do_nothing_function)
                while True:
                    output = img.grab()
                    imm = output[roi_co_ordinates[0][1]:roi_co_ordinates[1][1],
                             roi_co_ordinates[0][0]:roi_co_ordinates[1][0]]
                    value = get_threshold(imm)
                    if value != None:
                        threshold_value = value

                        break
    first = False
    import time
    frameCeount=False
    co=[]

    if True:
        output=img.grab()
        output = img.grab()
        outpu = output[roi_co_ordinates[0][1]:roi_co_ordinates[1][1],
                roi_co_ordinates[0][0]:roi_co_ordinates[1][0]]
        col = output[185, 800, 0]
        col1 = outpu[161, 296, 0]
        print("drago ko value",col1)
        print("normal",col)
        # write value in file
    while True:
        itr=itr+1

        output = img.grab()
        outpu = output[roi_co_ordinates[0][1]:roi_co_ordinates[1][1],
                roi_co_ordinates[0][0]:roi_co_ordinates[1][0]]
        col=output[185,800,0]
        col1 = outpu[161, 296, 0]
        print("color",col)
        isDown=image_processing(outpu,col,minDist,col1)
        if isDown:
            cv2.waitKey(200)
            release_down()
            continue
        if itr>=80:
            distCount=distCount+1
            if distCount<=5:
             minDist+=3
            elif distCount>=5 and distCount<12:
                minDist+=7
            elif distCount>=12:
                minDist+=12
            itr = 0

        if cv2.waitKey(15)&0xff==101:
            exit()