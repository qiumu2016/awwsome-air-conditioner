from django.http.response import JsonResponse
from django.shortcuts import render_to_response
import time
import datetime
import sqlite3
import string
import os
import json

dbpath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'db.sqlite3')

def cmpwind(s1,s2): # 0是小于，1是等于，2是大于
    if s1 == s2 :
        return 1
    elif s1 == 'low' :
        return 0
    elif s1 == 'mid' :
        if s2 == 'low' :
            return 2
        else :
            return 0
    else :
        return 2

def feecalc(s): #根据风速求费率
    if s == 'low' :
        return 0.3
    elif s == 'mid' :
        return 0.5
    else:
        return 1

class conditioner:
    def __init__(self):
        self.power_on = 0
        self.start_up = 0
        self.targetTemp = 0

host = conditioner()

def powerOn ():
    response = {}
    host.power_on = 1
    response['state'] = 'ok'
    return JsonResponse(response)

def setPara(request):
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        host.mode = request_post['model']
        host.tempHighLimit = request_post['temp_high_limit']
        host.tempLowLimit = request_post['temp_low_limit']
        host.targetTemp = request_post['default_target_temp']
        host.feeRateH = request_post['fee_rate_h']
        host.feeRateM = request_post['fee_rate_m']
        host.feeRateL = request_post['fee_rate_l']
        host.numRooms = request_post['num_rooms']
        host.numServe = request_post['num_serve']
        response['state'] = 'ok'
    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def startUp():
    response = {}
    host.start_up = 1
    response['state'] = 'ok'
    return JsonResponse(response)

class room:
    def __init__(self,roomid):
        self.roomid = roomid
        self.isCheckIn = 0
        self.isOpen = 0
        self.isServing = 0
        self.currentTemp = 27
        self.dispatchid = 0
        self.serviceid = 0
        self.checkInTime = 0

    def printRDR(self,request): #打印详单
        response = {}
        request_post = json.loads(request.body)
        if request_post:
            roomid = request_post['room_id']
            #dateIn = request_post['date_in']
            #dateOut = request_post['date_out']

            conn = sqlite3.connect(dbpath)
            cursor = conn.cursor()
            queryDetailSql = '''select room_id, start_time, (end_time - start_time), wind, fee_rate, fee
                                from AirCondition_details
                                where room_id = ?
            '''
            cursor.execute(queryDetailSql, (int(roomid),))
            values = cursor.fetchone()
            valuesStr = str(values)
            cursor.close()
            conn.close()

            printMode = 'RDR_{}'
            with open(printMode.format(roomid) + '.txt', 'a', encoding='utf-8') as f:
                f.write(valuesStr)

            response['state'] = 'ok'
        else:
            response['state'] = 'fail'
        return JsonResponse(response)

    def printInvoice(self,request): #打印账单
        response = {}
        request_post = json.loads(request.body)
        if request_post:
            roomid = request_post['room_id']
            #dateIn = request_post['date_in']
            #dateOut = request_post['date_out']
            self.isCheckIn = 0
            dispatchid = self.dispatchid
            if waitlist.__contains__(dispatchid) :
                del waitlist[dispatchid]
            else:
                del servicelist[dispatchid]
            serviceid = self.serviceid
            del serviceobjlist[serviceid]

            conn = sqlite3.connect(dbpath)
            cursor = conn.cursor()
            queryDetailSql = '''select sum(fee)
                                from AirCondition_details
                                where room_id = ?
            '''
            cursor.execute(queryDetailSql, (int(roomid),))
            values = cursor.fetchone()
            valuesStr = "".join(values)
            cursor.close()
            conn.close()

            printMode = 'Invoice_{}'
            with open(printMmode.format(roomid) + '.txt', 'a', encoding='utf-8') as f:
                f.write(valuesStr)

            response['state'] = 'ok'

            self.isCheckIn = 0
        else:
            response['state'] = 'fail'
        return JsonResponse(response)

roomlist = {}

class dispatch:
    dispatchcount = 0
    def __init__(self,roomid,wind,temp,fee_rate,mode):
        dispatch.dispatchcount += 1
        self.id = dispatch.dispatchcount
        self.roomid = roomid
        self.wind = wind
        self.target_temp = temp
        self.fee_rate = fee_rate
        self.fee = 0
        self.mode = mode
        self.feeprogress = 0
        #waittime
        #waitclock
        #serviceid
        #feeprogress

servicelist = {} #调度对象的服务队列
waitlist = {} #调度对象的等待队列

class serviceobj:
    servicecount = 0
    def __init__(self,roomid):
        serviceobj.servicecount += 1
        self.id = serviceobj.servicecount
        self.roomid = roomid
        self.status = 0
        self.clock = time.time() #服务开始时间
        #dispatchid
        
serviceobjlist = {} #服务对象队列

def checkRoomState(request): #查看房间状态
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        if not (roomlist.__contains__(roomid)):
            roomlist[roomid] = room(roomid)
        response['isCheckIn'] = roomlist[roomid].isCheckIn
        response['isOpen'] = roomlist[roomid].isOpen
        response['current_temp'] = roomlist[roomid].currentTemp
        if roomlist[roomid].isOpen == 1:
            response['isServing'] = roomlist[roomid].isServing
            obj = 0
            if servicelist.__contains__(roomlist[roomid].dispatchid) :
                obj = servicelist[roomlist[roomid].dispatchid]
            else:
                obj = waitlist[roomlist[roomid].dispatchid]
            response['wind'] = obj.wind
            response['target_temp'] = obj.target_temp
            response['fee_rate'] = obj.fee_rate
            response['fee'] = obj.fee
        response['state'] = 'ok'
    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def changeTargetTemp(request): #顾客更改空调目标温度
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        temp = request_post['target_temp']
        if roomlist.__contains__(roomid):
            if roomlist[roomid].isServing == 1 :
                servicelist[roomlist[roomid].dispatchid].target_temp = temp
            else:
                waitlist[roomlist[roomid].dispatchid].target_temp = temp
            response['state'] = 'ok'
        else:
            response['state'] = 'fail'

        connR = sqlite3.connect(dbpath)
        cursorR = connR.cursor()
        updateReportSql = '''update AirCondition_report
                             set schedule = schedule + 1, change_temp = change_temp + 1
                             where room_id = ?
        '''
        cursorR.execute(updateReportSql, (int(roomid),))
        cursorR.close()
        connR.commit()
        connR.close()
    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def changeFanSpeed(request): #顾客更改空调风速
    response = {}
    t2 = datetime.datetime.now()
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        fan = request_post['fan_speed']
        if roomlist.__contains__(roomid):
            obj = 0
            if roomlist[roomid].isServing == 1 :
                servicelist[roomlist[roomid].dispatchid].wind = fan
                servicelist[roomlist[roomid].dispatchid].fee_rate = feecalc(fan)

                obj = servicelist[roomlist[roomid].dispatchid]
            else:
                waitlist[roomlist[roomid].dispatchid].wind = fan
                waitlist[roomlist[roomid].dispatchid].fee_rate = feecalc(fan)

                obj = waitlist[roomlist[roomid].dispatchid]

            detailCheckInTime = roomlist[roomid].checkInTime
            detailModel = obj.mode
            detailCurrentTemp = roomlist[roomid].currentTemp
            detailWind = obj.wind
            detailFeeRate = obj.fee_rate
            detailFee = obj.fee
            conn = sqlite3.connect(dbpath)
            cursor = conn.cursor()
            queryDetailSql1 = '''select MAX(id)
                                 from AirCondition_details
                                 where room_id = ?
            '''
            cursor.execute(queryDetailSql1, (int(roomid),))
            updateId = cursor.fetchone()
            if (updateId != None):
                updateDetailSql1 = '''update AirCondition_details
                                      set end_time = ?, end_temp = ?, fee = ?
                                      where id = ?
                '''
                cursor.execute(updateDetailSql1, (datetime.datetime.now(), detailCurrentTemp, detailFee, int(roomid)))

            addDetailSql1 = '''insert into AirCondition_details
                               (check_in_time, room_id, model, operation, start_time, end_time, start_temp, end_temp, wind, fee_rate, fee)
                               values
                               (?, ?, ?, '0', ?, 0, ?, 0 ,?, ?, 0)
            '''
            cursor.execute(addDetailSql1, (detailCheckInTime, int(roomid), detailModel, datetime.datetime.now(),detailCurrentTemp, detailWind, detailFeeRate))
            t1 = roomlist[roomid].checkInTime
            s1 = t1.strftime("%Y%m%d%H%M%S")
            i1 = int(s1)
            s2 = t2.strftime("%Y%m%d%H%M%S")
            i2 = int(s2)

            cursor.close()
            conn.commit()
            conn.close()


            connR = sqlite3.connect(dbpath)
            cursorR = connR.cursor()
            updateReportSql = '''update AirCondition_report
                                 set time = time + ?, fee = fee + ? ,schedule = schedule + 1, change_wind = change_wind + 1
                                 where room_id = ?
            '''
            cursorR.execute(updateReportSql, ((i2 - i1) / 60, detailFee, int(roomid)))
            cursorR.close()
            connR.commit()
            connR.close()

            response['state'] = 'ok'
        else:
            response['state'] = 'fail'
    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def requestOn(request): #顾客请求开机
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        obj = dispatch(roomid,'mid',host.targetTemp,0.5,'cold') #调度
        if not roomlist.__contains__(roomid):
            roomlist[roomid] = room(roomid)
        if roomlist[roomid].isCheckIn == 0:
            roomlist[roomid].isCheckIn = 1
            roomlist[roomid].checkInTime = datetime.datetime.now()
        roomlist[roomid].isOpen = 1
        roomlist[roomid].currentTemp = request_post['current_room_temp']
        roomlist
        if len(servicelist)<host.numServe: #直接进入服务
            servicelist[obj.id] = obj
            serviceobject = serviceobj(roomid)
            obj.serviceid = serviceobject.id
            serviceobject.dispatchid = obj.id
            roomlist[roomid].serviceid = serviceobject.id
            roomlist[roomid].dispatchid = obj.id
            roomlist[roomid].isServing = 1
            serviceobject.status = 1
            serviceobjlist[serviceobject.id] = serviceobject
        else:
            flag = True
            target = 0
            for i in serviceobjlist.values():
                if flag:
                    target = i
                    flag = False
                else:
                    if cmpwind(target.wind , i.wind) == 2 :
                        target = i
                    elif cmpwind(target.wind , i.wind) == 1 :
                        if target.clock > i.clock :
                            target = i
            if cmpwind('mid' , target.wind) == 0: #从队中挤出一个
                del serviceobjlist[target.id]
                obj2 = servicelist[target.dispatchid]
                del servicelist[obj2]
                waitlist[obj2.id] = obj2
                obj2.waitclock = time.time()
                obj2.waittime = 2
                roomlist[target.roomid].isServing = 0
                servicelist[obj.id] = obj
                serviceobject = serviceobj(roomid) #新建一个服务对象
                obj.serviceid = serviceobject.id
                serviceobject.dispatchid = obj.id
                roomlist[roomid].isServing = 1
                serviceobject.status = 1
                serviceobjlist[serviceobject.id] = serviceobject
            elif cmpwind('mid' , target.wind) == 1: #进入等待队列
                waitlist[obj.id] = obj
                obj.waitclock = time.time()
                obj.waittime = 2
            else:
                waitlist[obj.id] = obj
                obj.waitclock = time.time()
                obj.waittime = -1
        response['modele'] = obj.mode
        response['target_temp'] =  obj.target_temp
        response['temp_high_limit'] = host.tempHighLimit
        response['temp_low_limit'] = host.tempLowLimit
        response['state'] = 'ok'

        connR = sqlite3.connect(dbpath)
        cursorR = connR.cursor()
        queryReportSql = '''select id
                            from AirCondition_report
                            where room_id = ?
        '''
        roomidInt = int(roomid)
        cursorR.execute(queryReportSql, (roomidInt,))
        idR = cursorR.fetchone()
        if (idR == None):
            addReportSql = '''insert into AirCondition_report
                              (room_id, switch, time, fee, schedule, change_temp, change_wind) 
                              values 
                              (?, 1, 0, 0, 1, 0, 0)
            '''
            cursorR.execute(addReportSql, (roomidInt,))
        else:
            updateReportSql = '''update AirCondition_report
                                 set switch = switch + 1
                                 where id = ?
            '''
            idR = str(idR)[1:-2]
            cursorR.execute(updateReportSql, (int(idR),))
        cursorR.close()
        connR.commit()
        connR.close()

    else:
        response['state'] = 'fail'

    return JsonResponse(response)

def requestOff(request): #顾客关机
    response = {}
    t2 = datetime.datetime.now()
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']

        roomlist[roomid].currentTemp = request_post['current_room_temp']
        dispatchid = roomlist[roomid].dispatchid

        if roomlist[roomid].isServing == 1:
            #servicelist[roomlist[roomid].dispatchid].wind = fan
            #servicelist[roomlist[roomid].dispatchid].fee_rate = feecalc(fan)
            obj = servicelist[roomlist[roomid].dispatchid]
        else:
            #waitlist[roomlist[roomid].dispatchid].wind = fan
            #waitlist[roomlist[roomid].dispatchid].fee_rate = feecalc(fan)
            obj = waitlist[roomlist[roomid].dispatchid]

        detailCurrentTemp = roomlist[roomid].currentTemp
        detailFee = obj.fee

        roomlist[roomid].dispatchid = 0
        roomlist[roomid].isOpen = 0

        if servicelist.__contains__(dispatchid) :
            del servicelist[dispatchid]
        else:
            del waitlist[dispatchid]
        if roomlist[roomid].isServing == 1 :
            serviceid = roomlist[roomid].serviceid
            roomlist[roomid].serviceid = 0
            roomlist[roomid].isServing = 0
            del serviceobjlist[serviceid]
        response['state'] = 'ok'

        conn = sqlite3.connect(dbpath)
        cursor = conn.cursor()
        queryDetailSql1 = '''select MAX(id)
                             from AirCondition_details
                             where room_id = ?
        '''
        cursor.execute(queryDetailSql1, (int(roomid),))
        updateId = cursor.fetchone()
        t1 = roomlist[roomid].checkInTime
        s1 = t1.strftime("%Y%m%d%H%M%S")
        i1 = int(s1)
        s2 = t2.strftime("%Y%m%d%H%M%S")
        i2 = int(s2)

        updateDetailSql = '''update AirCondition_details
                             set end_time = ?, end_temp = ?,fee = ?
                             where id = ?
        '''
        cursor.execute(updateDetailSql, ((t2, detailCurrentTemp, detailFee, updateId),))
        cursor.close()
        conn.commit()
        conn.close()

        connR = sqlite3.connect(dbpath)
        cursorR = connR.cursor()
        updateReportSql = '''update AirCondition_report
                             set time = time + ? , fee = fee + ?
                             where room_id = ?
        '''
        cursorR.execute(updateReportSql, (((i2 - i1) / 60, detailFee, int(roomid)),))
        cursorR.close()
        connR.commit()
        connR.close()

    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def requestInfo(request): #每分钟查看一次费用
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        if roomlist.__contains__(roomid) :
            response['isCheckIn'] = roomlist[roomid].isCheckIn
            response['isOpen'] = roomlist[roomid].isOpen
            response['isServing'] = roomlist[roomid].isServing
            obj = 0
            if servicelist.__contains__(roomlist[roomid].dispatchid) :
                obj = servicelist[roomlist[roomid].dispatchid]
            else:
                obj = waitlist[roomlist[roomid].dispatchid]
            response['wind'] = obj.wind
            response['current_temp'] = roomlist[roomid].currentTemp
            response['fee_rate'] = obj.fee_rate
            response['fee'] = obj.fee
            response['state'] = 'ok'
        else:
            response['state'] = 'fail'
    else:
        response['state'] = 'fail'
    return JsonResponse(response)

def printReport(request): #打印报表
    response = {}
    request_post = json.loads(request.body)
    if request_post:
        roomid = request_post['room_id']
        connR = sqlite3.connect(dbpath)
        cursorR = connR.cursor()
        queryReportSql = '''select *
                            from AirCondition_report
                            where room_id = ?
        '''
        cursorR.execute(queryReportSql,(int(roomid),))
        values = cursorR.fetchall()
        valuesStr = "".join(values)
        cursorR.close()
        connR.close()

        printMode = 'Report_{}'
        with open(printMode.format(roomid) + '.txt', 'a', encoding='utf-8') as f:
            f.write(valuesStr)

        response['state'] = 'ok'
    else:
        response['state'] = 'fail'
    return JsonResponse(response)