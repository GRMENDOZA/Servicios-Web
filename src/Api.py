import os
import sys
from flask import Flask, request, jsonify, render_template
import requests
import json
from datetime import datetime, timedelta
from google.cloud import storage
import datetime as dt
import pytz
import re

app = Flask(__name__)

def getMes(mes):
    if "EN" in mes or "JAN" in mes:
        return "01"
    if "FEB" in mes:
        return "02"
    if "MAR" in mes:
        return "03"
    if "ABR" in mes or "APR" in mes:
        return "04"
    if "MAY" in mes:
        return "05"
    if "JUN" in mes:
        return "06"
    if "JUL" in mes:
        return "07"
    if "AG" in mes or "AUG" in mes:
        return "08"
    if "SEP" in mes or "SET" in mes:
        return "09"
    if "OCT" in mes:
        return "10"
    if "NOV" in mes:
        return "11"
    if "DEC" in mes or "DIC" in mes:
        return "12"


##################Función no disponible es necesaria la VPN para poder hacer uso de la misma ################
def fechasDeEntregaVPN(trNumber):
    try:
        url = "https://pwasso.liverpool.com.mx:8443/rest/model/com/liverpool/OrderSearchActor/orderSearch?trackingNumber="+trNumber

        payload={}
        headers = {
        'brand': 'LP',
        'channel': 'web',
        'lp-auth-header': 'it8sjpiiDawcbETj8Ls0Qg%3D%3D',
        'Cookie': 'JSESSIONID=pDdPhaL4wxJF6cD_PRSVv5zKlWQYJTvrJ2PgMqdh6JMyA7MFPMJj!1584890370; genero=x; segment=fuero'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        # url = 'https://pwasso.liverpool.com.mx:8443/rest/model/com/liverpool/OrderSearchActor/orderSearch?trackingNumber='+trNumber
        # headers = {'brand': 'LP',
        #     'channel': 'web',
        #     'lp-correlation-id': 'TEST-CHINOS',
        #     'lp-auth-header':'it8sjpiiDawcbETj8Ls0Qg%3D%3D'}
        result = requests.get(url, headers=headers)
        resultjson = json.loads(result.text)
        # resultjson = response.json()
        statusCode=0
        status=""
        noProductos=0
        products=[]
        if resultjson["s"]== "0":
            i=0
            CAN = 0 #Cancelado
            ENR = 0
            FFR = 0 #Fecha Fuera de Rango
            FER = 0 #se agrega para escenario donde unos de los SKUs en pedido tiene fecha futura (Fecha En Rango)
            NINV = 0 #No hay inventario disponible
            NHFEE=0 #No hay Fecha Estimada de Entrega
            CC=0 #producto en click and collect
            for field in resultjson.keys():
                if field == "somsOrder":
                    for product in resultjson["somsOrder"]['commerceItems']:
                        i = i+1
                        if "estimatedDeliveryDate" in product.keys():
                            try:
                                if ("no es posible mostrar la fecha de entrega" in product["estimatedDeliveryDate"]) or ("no contamos con inventario en bodega" in product["EDDErrorCode"].lower()):
                                    fecha = " "
                                    # FFR = FFR+1: #or ("no contamos con inventario en bodega" in product["EDDErrorCode"].lower())
                                    fecha = " "
                                    # FFR = FFR+1
                                    NINV += 1
                                    
                                else:                                  
                                    
                                    fecha = "Fecha de Entrega: "  + product["estimatedDeliveryDate"]
                                    dates = product["estimatedDeliveryDate"].upper().split("-")
                                    f = dates[len(dates)-1].strip().split(" ")
                                    d=""
                                    x = datetime.now()
                                    if len(f) == 3:
                                        if getMes(f[2]) == "01" and x.month == 12:
                                            d = f[0]+"-"+getMes(f[2])+"-"+str(x.year+1)
                                        else:
                                            d = f[0]+"-"+getMes(f[2])+"-"+str(x.year)
                                    if len(f) == 5:
                                        d = f[0]+"-"+getMes(f[2])+"-"+f[4]
                                    dateFromString = datetime.strptime(d, "%d-%m-%Y")
                                    if "al modulo a recoger" in product["itemStatus"]:
                                        CC = CC+1
                                    if x.date() <= dateFromString.date():
                                        FER = FER+1
                                    else: #se agrega para escenario donde unos de los SKUs en pedido tiene fecha futura (Fecha En Rango)
                                        FFR = FFR+1
                            except:
                                
                                fecha = " "
                        else:
                            NHFEE = NHFEE+1

                        if product["itemStatus"] == "Cancelado":
                            fecha = " "
                            CAN = CAN + 1
                        # if product["itemStatus"] == "Pedido entregado" or product["itemStatus"] == "Regalo Entregado":
                        #     ENR = ENR + 1
                        producto = {
                            'sku':product["SkuId"],
                            'displayName': product["DisplayName"],
                            'imgURL':product["SmallImage"],
                            'estimatedDeliveryDate':fecha,
                            'status':product["itemStatus"]
                        }
                        #print(producto)
                        products.append(producto)
                if field == "order":
                    for deliveryInfo in resultjson["order"]['deliveryInfo']:
                        for product in deliveryInfo["packedList"]:
                            i = i+1
                            if "estimatedDeliveryDate" in product.keys():
                                try:
                                    if ("No contamos con inventario en bodega" in product["EDDErrorCode"]) or ("no es posible mostrar la fecha de entrega" in product["estimatedDeliveryDate"]): #or not product["estimatedDeliveryDate"]:
                                        fecha = " "
                                        # FFR = FFR+1
                                        NINV = NINV+1
                                    else:
                                        fecha = "Fecha de Entrega: "  + product["estimatedDeliveryDate"]
                                        if deliveryInfo["eddMessage"] != None:
                                            fecha = deliveryInfo["eddMessage"] + " " +fecha
                                        dates = product["estimatedDeliveryDate"].upper().split("-")
                                        f = dates[len(dates)-1].strip().split(" ")
                                        d=""
                                        x = datetime.now()
                                        if len(f) == 3:
                                            if getMes(f[2]) == "01" and x.month == 12:
                                                d = f[0]+"-"+getMes(f[2])+"-"+str(x.year+1)
                                            else:
                                                d = f[0]+"-"+getMes(f[2])+"-"+str(x.year)
                                        if len(f) == 5:
                                            d = f[0]+"-"+getMes(f[2])+"-"+f[4]
                                        dateFromString = datetime.strptime(d, "%d-%m-%Y")
                                        if "al modulo a recoger" in product["itemStatus"]:
                                            CC = CC+1
                                        if x.date() <= dateFromString.date():
                                            FER = FER+1
                                        else: #se agrega para escenario donde unos de los SKUs en pedido tiene fecha futura (Fecha En Rango)
                                            FFR = FFR+1
                                except:
                                    fecha = " "
                            else:
                                NHFEE = NHFEE+1
                            if product["itemStatus"] == "Cancelado":
                                fecha = " "
                                CAN = CAN + 1
                            # if product["itemStatus"] == "Pedido entregado" or product["itemStatus"] == "Regalo Entregado":
                            #     ENR = ENR + 1
                            producto = {
                                'sku':product["skuID"],
                                'displayName': product["displayName"],
                                'imgURL':product["smallImage"],
                                'estimatedDeliveryDate':fecha,
                                'status':product["itemStatus"]
                            }
                            products.append(producto)
                statusCode=200
                if CAN == i:
                    status = "CAN"
                elif CC == i:
                    status = "CC"
                elif NINV > 0: #Se agrega para escenario donde no hay inventario disponible
                    status = "NINV"
                elif FER > 0: #se agrega para escenario donde unos de los SKUs en pedido tiene fecha futura (Fecha En Rango)
                    status = "FER"
                elif NHFEE == i:
                    status = "NHFEE"
                elif ENR == i:
                    status = "ENR"
                elif FFR == i:
                    status = "FFR"
                elif ENR + CAN + FFR + NHFEE == i:
                    status = "CANENR"
                elif CAN > 0 or ENR > 0 or FFR > 0 or NHFEE>0:
                    status = "OK" #Se cambio de EP a OK por reglas de CAT
                else:
                    status="OK"
                noProductos=i
        else:
            statusCode=400
            status="NOK"
            noProductos=0
            products=[]
        jsonRaw = {
                'statusCode': statusCode,
                'status':status,
                'noProducts':noProductos,
                'products': products
            }
        return jsonRaw
    except BaseException as error:
        statusCode=401
        status='An exception occurred: {}'.format(error)
        noProductos=0
        products=[]
        jsonRaw = {
                'statusCode': statusCode,
                'status':status,
                'noProducts':noProductos,
                'products': products
            }
        return jsonRaw

def validarCorreo(trNumber):
    expresion_regular = r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"
    return re.match(expresion_regular, trNumber)
    


def getErrorResponse(error):
    jsonRaw = {
        'fulfillmentMessages': [
            {
            'text': {
                    'text': [
                        '{}'.format(error)
                    ]
                }
            }
        ]
    }
    jsonResponse = app.response_class(
        response=json.dumps(jsonRaw),
        status=400,
        mimetype='application/json'
    )
    return jsonResponse

def isWorkingTimePedidos():
    isWork = 1
    tz_MX = pytz.timezone('America/Mexico_City')
    MX_now = dt.datetime.now(tz_MX).hour
    print(MX_now)
    if(MX_now>=8 and MX_now<19):
        isWork = 1
        return isWork
    return isWork

def fechasDeEntregaDialogFlow(trNumber):
    try:
        resultjson = fechasDeEntregaVPN(trNumber)
        products=[]
        print(resultjson)
        asesor = ""
        if resultjson["status"]== "OK" or resultjson["status"]== "FER":
            for product in resultjson["products"]:
                producto = {
                    "card": {
                        "title": "*"+product["displayName"] +"*\nCódigo de producto:\n*"+product["sku"]+"*",
                        "subtitle": product["status"]+"\n*"+product["estimatedDeliveryDate"]+"*",
                        "imageUri": product["imgURL"],
                        "buttons": [
                            {
                                "text": "Ver mi pedido",
                                "postback": "https://www.liverpool.com.mx/tienda/users/orderHistory?SearchOrder=true&TrackingNo=0"+trNumber
                            }
                        ]
                    }
                }
                products.append(producto)
                
            producto = {
                "card": {
                    "title": "Si aún tienes dudas con la información que te presentamos, por favor *indícanos* en qué te podemos ayudar de acuerdo con las siguientes opciones:\n\n-Conocer fecha de entrega\n-Cancelar pedido\n-Seguimiento a mi devolución\n-Cambio de domicilio\n\nEnvía la palabra *asesor* y después un breve comentario de acuerdo con el menú anterior.\nEn un momento serás atendido",
                    "subtitle": None,
                    "imageUri": None,
                    "buttons": [
                        {
                            "text": None,
                            "postback": None
                        }
                    ]
                }
            }
            products.append(producto)

            # producto = {
            #         "card": {
            #             "title": "¿Necesitas que te ayude en algo más?",
            #             "subtitle": None,
            #             "imageUri": None,
            #             "buttons": [
            #                 {
            #                     "text": None,
            #                     "postback": None
            #                 }
            #             ]
            #         }
            #     }
            # products.append(producto)
            # asesor = "asesor-Seg2Incumplimiento-CONS PEDIDO"
        elif resultjson["status"]== "NOK" and resultjson["noProducts"] == 0:
            if "@" in trNumber:                 
                if validarCorreo(trNumber)== None: 
                    asesor = "tag-CONS PEDIDO"
                    products=[{"text": {"text": ["Lo sentimos, la dirección de correo electrónico que nos compartes no es válida, por favor verifícalo y vuelve a intentar.  Gracias "]}}]
                else:
                    products=[{"text": {"text": ["Gracias por favor compártenos la siguiente información:  fecha, código del producto y monto de tu compra, en un momento un asesor te atenderá"]}}]
                    asesor = "asesor-Seg2Incumplimiento-CONS PEDIDO" #"asesor-Seg1Fecha de entrega-CONS PEDIDO"
            else:
                asesor = "tag-CONS PEDIDO"
                products=[{"text": {"text": ["El número de pedido que capturaste es incorrecto, te pido lo verifiques y lo teclees nuevamente."]}}]        
        else:
            print('Aqui ando')
            ##### Operación normal ########
            # products=[{"text": {"text": ["En un momento un asesor te atendera"]}}]
            # if resultjson["status"]== "FFR":
            #     asesor = "asesor-Seg2Incumplimiento-CONS PEDIDO"
            # else:
            #     asesor = "asesor-Seg1Fecha de entrega-CONS PEDIDO"
            ##### Operación normal ########

            ##### Workaround por saturación de asesores ########
            fileName = 'wa/volumetria_seguimiento_wa.csv'
            bucketName = 'liv-pro-dig-chatbot-bkt01'
            client = storage.Client()
            bucket = client.get_bucket(bucketName)
            print(bucket)
            print(trNumber)
            blob = bucket.get_blob(fileName)
            pedidos = blob.download_as_string().decode("utf8")
            # if((resultjson["status"]== "FFR") and ('\n{}\r'.format(trNumber) in pedidos)):

            if('\n{}\r'.format(trNumber) in pedidos):
                print('Entra a pedidos en archivo\n')
                products=[{"text": {"text": ["La fecha estimada de entrega de tu mercancía es de 1 a 10 días a partir de hoy. Espera nuestro aviso de confirmación."]}}]
            else:
                print('aqui ando de nuevo')
                print(isWorkingTimePedidos())
                if isWorkingTimePedidos() == 1:
                    if resultjson["status"]== "CC" or resultjson["status"]== "NINV" or resultjson["status"]== "CAN":
                        # if resultjson["status"]== "FER":
                            #  producto = {
                            #             "card": {
                            #                 "title": "Escribe *asesor*, si aún tienes dudas con la información que te presentamos y en un momento serás atendido",
                            #                 "subtitle": None,
                            #                 "imageUri": None,
                            #                 "buttons": [
                            #                     {
                            #                         "text": None,
                            #                         "postback": None
                            #                     }
                            #                 ]
                            #             }
                            #         }
                            # products=[{"text": {"text": ["Escribe *asesor*, si aún tienes dudas con la información que te presentamos y en un momento serás atendido"]}}]
                        # products.append(producto)
                        if (resultjson["status"]== "CC"):
                                products=[{"text": {"text": ["¡Tu pedido está listo!\n\nTe invitamos a acudir al modulo de click & collect de la tienda seleccionada para recoger tu pedido.\n\nGracias por permitirnos ser parte de tu vida."]}}]
                        if (resultjson["status"]== "NINV"):
                            if(trNumber[0]==9):
                                products=[{"text": {"text": ["¡Hola!\n\nGracias por contactarnos, estamos trabajando para poderte brindar la fecha de entrega de tu pedido, tan pronto nos sea posible te contactaremos para coordinar la entrega.\n\n Si requieres mayor información, marca desde tu celular al *7171, opción 2 del menú principal y opción 2 del submenú.\n\n Gracias por dejarnos ser parte de tu vida."]}}]
                                # asesor = "asesor-Seg2Incumplimiento-CONS PEDIDO"
                            else:
                                products=[{"text": {"text": ["¡Hola!\n\nTu pedido se encuentra en orden, por el momento no podemos brindarte una fecha precisa de entrega.\n\nEn 72 horas hábiles podremos brindarte mayor información.\n\nGracias por dejarnos ser parte de tu vida."]}}]
                        if (resultjson["status"]== "CAN"):
                                products=[{"text": {"text": ["Estimado cliente\n\nVeo que tu pedido se encuentra cancelado, por lo que te pedimos esperar tu devolución\n\nTu saldo se verá reflejado de la siguiente manera de acuerdo a tu forma de pago:\n\n* Tarjetas Liverpool y Liverpool Visa en 5 días hábiles.\n\n*Tarjetas de crédito externas en 5 días hábiles.\n\n* Monedero digital en 5 días hábiles\n\n* Tarjetas de débito BBVA, Citibanamex, BanCoppel y PayPal en 10 días hábiles.\n\n* Otras tarjetas de débito, pagos referenciados (tiendas de conveniencia) y transferencias electrónicas, tu dinero estará listo en 10 días hábiles para recoger en tienda\n\nEscribe *asesor*, si aun tienes dudas con la información que te presentamos y en un momento serás atendido"]}}]
                    else:
                        products=[{"text": {"text": ["Lo lamento, por el momento no he logrado identificar tu pedido. Por favor escribe la palabra *asesor* para ser atendido por uno de nuestros ejecutivos."]}}]
                        #asesor = "asesor-Seg2Incumplimiento-CONS PEDIDO" "asesor-Seg1Fecha de entrega-CONS PEDIDO"
                else:
                    products=[{"text": {"text": ["Para brindarte atención personalizada, por favor ponte en contacto con nosotros en un horario de 8am a 7pm.\n¡Gracias por dejarnos ser parte de tu vida!"]}}]
            ##### Workaround por saturación de asesores ########
        jsonRaw = {
                    "fulfillmentText":asesor,
                    "fulfillment_messages": products
                }
        jsonResponse = app.response_class(
        response=json.dumps(jsonRaw),
        status=200,
        mimetype='application/json'
        )
        return jsonResponse
    except BaseException as error:
        return getErrorResponse(error)


def putTag(p):
    jsonRaw ={
        "fulfillmentText": p,
        "fulfillmentMessages": [{"text": {"text": ["En un momento uno de nuestros asesores te atenderá. Debido al alto volumen de solicitudes que estamos recibiendo, nuestro tiempo máximo de respuesta será de 90 minutos"]}}]
    }
    jsonResponse = app.response_class(
        response=json.dumps(jsonRaw),
        status=200,
        mimetype='application/json'
        )
    return jsonResponse


@app.route('/consultaFEE', methods=['POST'])
def consultaSaldo():
    try:
        if(request.headers['Content-Type'] == 'application/json'):
            content = json.loads(request.get_data())
            if(content != None):
                pedido = content['pedido']
                p = pedido.split('-')
                if p[0] == "asesor":
                    return putTag(pedido)
                else:
                    return fechasDeEntregaDialogFlow(pedido)
            return getErrorResponse('No content')
        return getErrorResponse('Not correct Content-Type')
    except BaseException as error:
        return getErrorResponse(error)

@app.route('/page', methods=['GET'])
def pagina_inicial():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
    # fechasDeEntregaDialogFlow('1392422071')
    # print(isWorkingTimePedidos())