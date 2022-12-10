import cv2
import pytesseract
import os
import numpy as np
import requests
import drivers
import time
import RPi.GPIO as GPIO
import threading

url = 'http://5aca-2804-14c-8793-8e03-85f9-a558-fec4-c077.sa.ngrok.io/api/garagem'

captou_sensor_entrada = False
captou_sensor_saida = False

GPIO.setmode(GPIO.BOARD)

pir_L = 12
pir_R = 16

GPIO.setup(pir_L, GPIO.IN)
GPIO.setup(pir_R, GPIO.IN)

lcd_L = drivers.Lcd(0x27)
lcd_R = drivers.Lcd(0x23)

gate_L = 11
gate_R = 13

GPIO.setup(gate_L, GPIO.OUT)
GPIO.setup(gate_R, GPIO.OUT)

def entrada_detect():
    while True:
        if GPIO.input(pir_L) == 1:
            global captou_sensor_entrada
            captou_sensor_entrada = True

def saida_detect():
    while True: 
        if GPIO.input(pir_R) == 1:
            global captou_sensor_saida
            captou_sensor_saida = True

def main():
    setup_inicial()
    conected = False
    conect_init = 0
    conect_max = 5
    while(conected == False):
        init_1 = time.time()
        conected = check_internet()
        if conected == False and conect_init <= 0:
            limpa_LCD(True)
            print_LCD('Não Conectou', 'na internet', False)
            conect_init = conect_max
        fim_1 = time.time()
        conect_init = conect_init - (fim_1 - init_1)
    
    limpa_LCD(False)
    print_LCD('Iniciando', 'Hoptimum', False)
    time.sleep(3)
    limpa_LCD(False)
    detectar_placa()
    
def check_internet():
    url_google = 'https://www.google.com'
    timeout = 5
    try:
        requests.get(url_google, timeout=timeout)
        return True
    except:
        return False
    
def setup_inicial():
    exc_1 = threading.Thread(target = entrada_detect)
    exc_2 = threading.Thread(target = saida_detect)

    exc_1.start()
    exc_2.start()
    limpa_LCD(True)
    limpa_LCD(False)

def print_LCD(linha1, linha2, entrada):
    if entrada == False:
        lcd_R.lcd_display_string(linha1, 1)
        lcd_R.lcd_display_string(linha2, 2)
    else:
        lcd_L.lcd_display_string(linha1, 1)
        lcd_L.lcd_display_string(linha2, 2)

    
def limpa_LCD(entrada):
    if entrada == False:
        lcd_R.lcd_clear()
    else:
        lcd_L.lcd_clear()
    
def abrir_garagem(entrada, high):
    if entrada == True:
        if high == True:
            GPIO.output(gate_L, GPIO.HIGH)
        else:
            GPIO.output(gate_L, GPIO.LOW)
    else:
        if high == True:
            GPIO.output(gate_R, GPIO.HIGH)
        else:
            GPIO.output(gate_R, GPIO.LOW)

def enviar_placa_conexao(nome_placa, direcao):
    obj = {'placa': nome_placa, 'status': direcao}

    x = requests.post(url, json = obj)
    return x.status_code

def ler_contornos(imagem_entrada, contornos, sensor):
    saida = ""
    for c in contornos:
        perimetro = cv2.arcLength(c, True)
        if perimetro > 250 and perimetro < 450 :
            aproximado = cv2.approxPolyDP(c, 0.03*perimetro, True)
            if len(aproximado) == 4:
                (x, y, largura, altura) = cv2.boundingRect(c)
                if(altura < largura):
                    cv2.rectangle(imagem_entrada, (x, y), (x+largura, y+altura), (0,255,0), 2)
                    result = imagem_entrada[y:y+altura, x:x+largura]
                    if (sensor == True):
                        saida_tesseract = ler_tesseract(result)
                        if(len(saida_tesseract) > 6):
                            saida = saida_tesseract
    return saida      
        

def ler_tesseract(imagem):   
    if imagem is None:
        return
    
    imagem_resize = cv2.resize(imagem, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
    imagem_cinza = cv2.cvtColor(imagem_resize, cv2.COLOR_BGR2GRAY)
    blank, binario = cv2.threshold(imagem_cinza, 40, 255, cv2.THRESH_BINARY)
    elemEstruturada = np.ones((5,5),np.uint8)

    imgFechada = cv2.morphologyEx(binario, cv2.MORPH_CLOSE, elemEstruturada)

    config = r'-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 --psm 6'
    saida = pytesseract.image_to_string(imgFechada, lang='eng', config=config)
    
    saida = saida.strip()
    lista_valores = saida.split('\n')
    result = ''
    for x in lista_valores:
        x = x.replace(" ", "")
        if len(x) == 7:
            result = x
            
    if len(result) == 7:
        return result
    else:
        return ""

def detectar_placa():
    cam = cv2.VideoCapture(0)
    placa_saida = ""
    placa_entrada = ""
    
    sensor_entrada = False
    sensor_saida = False
    
    garagem_entrada_abriu = False
    garagem_saida_abriu = False
    
    temporizador_sensor_entrada = 0
    temporizador_sensor_saida = 0
    temporizador_garagem_entrada = 0
    temporizador_garagem_saida = 0
    
    intervalo_garage_open = 3
    intervalo_sensor = 10
    
    global captou_sensor_entrada
    global captou_sensor_saida
    
    while cam.isOpened():
        ret, frame = cam.read()
        if(ret == False):
            break
        
        placa_entrada_pre = ""
        placa_saida_pre = ""
        
        altura_frame, largura_frame, frame_c = frame.shape
        
        frame_entrada = frame[:, :(int(largura_frame/2))]
        frame_saida = frame[:, (int(largura_frame/2)):]
        
        init = time.time()
        
        imagem_cinza_entrada = cv2.cvtColor(frame_entrada, cv2.COLOR_BGR2GRAY)
        blank_entrada, binario_entrada = cv2.threshold(imagem_cinza_entrada, 50, 255, cv2.THRESH_BINARY)
        contornos_entrada, hierarquia_entrada = cv2.findContours(binario_entrada, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        
        imagem_cinza_saida = cv2.cvtColor(frame_saida, cv2.COLOR_BGR2GRAY)
        blank_saida, binario_saida = cv2.threshold(imagem_cinza_saida, 50, 255, cv2.THRESH_BINARY)
        contornos_saida, hierarquia_saida = cv2.findContours(binario_saida, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        
        if captou_sensor_entrada == True:
            captou_sensor_entrada = False
            if(garagem_entrada_abriu == False):
                temporizador_sensor_entrada = intervalo_sensor
        
        if captou_sensor_saida == True:
            captou_sensor_saida = False
            if(garagem_saida_abriu == False):
                temporizador_sensor_saida = intervalo_sensor
                
        if(temporizador_sensor_entrada > 0):
            sensor_entrada = True
        else:
            sensor_entrada = False
        
        if(temporizador_sensor_saida > 0):
            sensor_saida = True
        else:
            sensor_saida = False
        
        placa_entrada_pre = ler_contornos(frame_entrada, contornos_entrada, sensor_entrada)
        placa_saida_pre = ler_contornos(frame_saida, contornos_saida, sensor_saida)
        
        if(len(placa_entrada_pre) == 7):
            conected_entrada = enviar_placa_conexao(placa_entrada_pre, 'ENTROU')
            if(conected_entrada == 200):
                temporizador_sensor_entrada = 0
                sensor_entrada = False
                temporizador_garagem_entrada = intervalo_garage_open
                abrir_garagem(True, True)
                limpa_LCD(True)
                print_LCD('Bem Vindo', placa_entrada_pre, True)
                garagem_entrada_abriu = True
            else:
                print_LCD('Placa não', 'Registrada', True)
            
        if(len(placa_saida_pre) == 7):
            conected_saida = enviar_placa_conexao(placa_saida_pre, 'SAIU')
            if(conected_saida == 200):
                temporizador_sensor_saida = 0
                sensor_saida = False
                temporizador_garagem_saida = intervalo_garage_open
                abrir_garagem(False, True)
                limpa_LCD(False)
                print_LCD('Volte mais', placa_saida_pre, False)
                garagem_saida_abriu = True
            else:
                print_LCD('Placa não', 'Registrada', False)       
        
        fim = time.time()
        
        if(temporizador_sensor_entrada > 0):
            temporizador_sensor_entrada = temporizador_sensor_entrada - (fim - init)
            
        if(temporizador_sensor_saida > 0):
            temporizador_sensor_saida = temporizador_sensor_saida - (fim - init)
        
        if(temporizador_garagem_entrada > 0):
            temporizador_garagem_entrada = temporizador_garagem_entrada - (fim - init)
        elif(garagem_entrada_abriu == True):
            limpa_LCD(True)
            abrir_garagem(True, False)
            garagem_entrada_abriu = False
        
        if(temporizador_garagem_saida > 0):
            temporizador_garagem_saida = temporizador_garagem_saida - (fim - init)
        elif(garagem_saida_abriu == True):
            limpa_LCD(False)
            abrir_garagem(False, False)
            garagem_saida_abriu = False
        
        if cv2.waitKey(1) & 0xff == ord('q'):
            break
        
    cam.release()
    cv2.destroyAllWindows()
    

if __name__ == '__main__':
    main()