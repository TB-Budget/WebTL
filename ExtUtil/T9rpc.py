# coding=UTF-8
'''
Модуль удаленного вызова процедур Турбо9
На основе func_rpc.php

Данный проект является свободным программным обеспечением. Вы вправе распространять его
и/или модифицировать в соответствии с условиями версии 2.1 либо по вашему выбору с условиями
более поздней версии Стандартной Общественной Лицензии Ограниченного Применения GNU,
опубликованной Free Software Foundation.

Мы распространяем этот проект в надежде на то, что он будет вам полезен, однако
НЕ ПРЕДОСТАВЛЯЕМ НА НЕГО НИКАКИХ ГАРАНТИЙ, в том числе ГАРАНТИИ ТОВАРНОГО СОСТОЯНИЯ ПРИ ПРОДАЖЕ
и ПРИГОДНОСТИ ДЛЯ ИСПОЛЬЗОВАНИЯ В КОНКРЕТНЫХ ЦЕЛЯХ. Для получения более подробной информации
ознакомьтесь со Стандартной Общественной Лицензией Ограниченного Применений GNU.

Вместе с данным проектом вы должны были получить экземпляр Стандартной Общественной Лицензии
Ограниченного Применения GNU. Если вы его не получили, сообщите об этом в Software Foundation, Inc.,
59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
'''

class T9RPCError(Exception):
    """Ошибка протокола или подкулючения T9"""
    pass


#Блок сериализации- десериализации
def unserialize(Str, Len):
    '''Выборка данных из строки'''
    Res=Str[:Len]
    Str=Str[Len:]
    return (Res, Str)

def int_serialize(Val,Size=4):
    '''Упаковка целого числа фиксированного размера'''
    Str=""
    for i in xrange(0,Size):
        (Val,Chr)=divmod(Val,256)
        Str=Str+chr(Chr)
    return Str

def int_unserialize(Str,Size=4):
    '''Распаковка целого числа фиксированного размера'''
    Res=0
    for i in xrange(Size-1,-1,-1):
        Res=Res*256+ord(Str[i])
    Str=Str[Size:]
    return (Res, Str)
        
def int_ex_serialize(Val):
    '''Упаковка целого числа вместе с его размером'''
    if (Val > 0) and (Val <= 253):
        return chr(Val)
    elif (Val >= -32768) and (Val <= 32767):
        return chr(254)+int_serialize(Val,2)
    else:
        return chr(255)+int_serialize(Val,4)
    
def int_ex_unserialize(Str):
    '''Распаковка целого числа, запакованного вместе с его размером'''
    (Res, Str)=int_unserialize(Str,1)
    if Res<=253:
        return (Res, Str)
    elif Res==254:
        return int_unserialize(Str,2)
    else:
        return int_unserialize(Str,4)

#def str_serialize(Val):
#    '''Упаковка строки (добавление длины) v63'''
#    Len=len(Val)
#    if Len<255:
#        return chr(Len)+Val
#    else:
#        return chr(255)+int_serialize(Len)+Val


def str_serialize(Val):
    '''Упаковка строки (добавление длины)'''
    if not Val:
        return chr(0)
    else:
        return chr(1) + int_ex_serialize(len(Val)) + Val;


#def str_unserialize(Str):
#    '''Распаковка строки по длине из потока v63'''
#    (Len, Str)=int_unserialize(Str,1)
#    if Len==255:
#        (Len, Str)=int_unserialize(Str,4)
#    return unserialize(Str, Len)
def str_unserialize(Str):
    (code, Str) = int_unserialize(Str, 1)
    if not code:
        return ("", Str)
    elif code == 1:
        (Len, Str) = int_ex_unserialize(Str)
        return unserialize(Str, Len)
    else:
        raise T9RPCError("RPC protocol error: unicode not supported")


import uuid 
def guid_serialize(Id):
    '''Упаковка GUID'''
    Res=uuid.UUID(Id).bytes_le
    return Res
    
def guid_unserialize(Str):
    '''Распаковка GUID в текстовое представление (у ДИЦ не было, использовалась простая распаковка)'''
    (Bin, Str)=unserialize(Str,16)
    Guid=uuid.UUID(bytes_le=Bin).hex
    Guid=Guid.upper()
    Guid="{"+Guid[0:8]+"-"+Guid[8:12]+"-"+Guid[12:16]+"-"+Guid[16:20]+"-"+Guid[20:]+"}"
    return (Guid,Str)
 
def exception_unserialize(Str):
    '''Распаковка ошибки'''
    (Class, Str)=str_unserialize(Str)
    (Code, Str)=int_ex_unserialize(Str)
    (Mess, Str)=str_unserialize(Str)
    return (Mess, Str)
    
##Сетевое взаимодействие
import socket
NetRetOk=chr(1)
NetRetError=chr(2)
NetRetCallback=chr(3)

def recv(Sock, Len):
    '''Получение данных из сокета'''
    Res = "";
    while (Len > 0): 
        Str = Sock.recv(Len);
        if not Str:
            raise T9RPCError("Socket read error")
        Len-=len(Str)
        Res+=Str
    return Res;

def recv_packet(Sock):
    '''Получение пакета из сокета'''
    Header=recv(Sock,12)
    if Header[:4]<>"TBNP":
        raise T9RPCError("RPC packet error")
    Header=Header[4:]
    (Count1,Header)=int_unserialize(Header)
    (Count2,Header)=int_unserialize(Header)
    Str1=recv(Sock,Count1)
    Str2=recv(Sock,Count2)
    return Str1

def send_packet(Sock,Data1,Data2):
    '''Отправка пакета'''
    Packet="TBNP"+int_serialize(len(Data1))+int_serialize(len(Data2))+Data1+Data2
    Res=Sock.send(Packet)
    if not Res:
        raise T9RPCError("Socket write error")
    return Res

def communicate(Sock,Data1):
    '''обмен данными'''
    send_packet(Sock,Data1,"")
    Res=recv_packet(Sock)
    Code=Res[0]
    Res=Res[1:]
    if Code==NetRetError:
        raise T9RPCError("RPC call return error: "+exception_unserialize(Res)[0])
    elif Code==NetRetCallback:
        raise T9RPCError("RPC callback not supported")
    return Res

##Работа с сессиями и соединениями
NetCmdNegotiating=1
NetCmdCall=2
NetCmdRelease=5
NetCmdReconnect=6
NetCmdDisconnect=7
NetProtocolVersion1=7
NetProtocolVersion2=4
diUser=3+9
dispIn=64
dispOut=128
dispString=6

ProxyService="T9WebProxy"
ProxyGUID="{9B4F96CB-39A1-4EA7-B3BB-052203517FD9}"

def connect(Server,Port,Service,Guid,Info,SID,RemoteAddr,UserAgent):
    '''Подключение к серверу
    
    Возвращает кортеж из сокета и информации подключения
    '''
    if Info==None:
        Info=["","","",""]
    if Guid==None or Guid=="":
        Guid=ProxyGUID
    if Service==None or Service=="":
        Service=ProxyService
    Sock=socket.create_connection((Server,Port))
    Data=chr(NetCmdNegotiating)+chr(NetProtocolVersion1)+chr(NetProtocolVersion2) \
    +str_serialize(Service)+guid_serialize(Guid) \
    +str_serialize(SID)+str_serialize("")+str_serialize(RemoteAddr)+str_serialize(UserAgent)+chr(0)+chr(0)+chr(0)
    Res=communicate(Sock,Data)
    (Info[0],Res)=guid_unserialize(Res)
    (Info[1],Res)=int_ex_unserialize(Res)
    (Info[2],Res)=int_ex_unserialize(Res)
    (Info[3],Res)=guid_unserialize(Res)
    return (Sock, Info)

def reconnect(Server,Port,Info):
    '''Восстановление подключения по информации
    
    Возвращает кортеж из сокета и информации подключения'''
    Sock=socket.create_connection((Server,Port))
    Data=chr(NetCmdReconnect)+chr(NetProtocolVersion1)+chr(NetProtocolVersion2) \
    +guid_serialize(Info[0])+int_ex_serialize(Info[1])+int_ex_serialize(Info[2])+guid_serialize(Info[3])
    communicate(Sock,Data)
    return (Sock, Info)

def call(Sock,Method_idx,Arg):
    '''Вызов процедуры по номеру через встроенный диспетчер'''
    Data=chr(NetCmdCall)+chr(diUser+Method_idx)+chr(1)+chr(dispOut+dispString)+chr(dispIn+dispString)+str_serialize(Arg)
    Res=communicate(Sock,Data)
    (N,Res)=int_ex_unserialize(Res)
    if N<>1:
        raise T9RPCError("RPC protocol error: invalid parameter count: "+str(N))
    Res=int_unserialize(Res,1)[1]
#    if T<>chr(dispOut+dispString):
#        raise AssertionError("RPC protocol error: invalid result returned")
    Res=int_unserialize(Res,1)[1]
    return str_unserialize(Res)[0]

def disconnect(Sock):
    '''Отключение от сервера'''
    communicate(Sock,chr(NetCmdDisconnect))
    Sock.close()

def standby(Sock):
    '''Приостановка обмена данными'''
    communicate(Sock,chr(NetCmdRelease))
    Sock.close()
    
def login(Sock,ProcServ,DataServ,Infobase,Login,Password,Role):
    '''Авторизация на сервере, подключение к функционалу Турбо9'''
    try:
        call(Sock, 0, ProcServ+"|"+DataServ+"|"+Infobase\
             +"|"+Login+"|"+Password+"|"+Role)
    except:
        disconnect(Sock)
        raise
    
def proc_call(Sock,aClass,aProc,aParam=""):
    '''Вызов функции через встроенный диспетчер
    Поддерживаются только функции с одним строковым параметром, возвращающие строку'''
    return call(Sock,1,aClass+"|"+aProc+"|"+aParam)

import xmlrpclib
def xml_call(Sock,fName,Params):
    '''Вызов функции через XML-RPC диспетчер прикладного уровня'''
    Request = xmlrpclib.dumps(Params, fName, encoding="windows-1251")
    Resp = call(Sock,1,"XMLRPC.Calling|Caller|"+Request)
    Res = xmlrpclib.loads(Resp)
    return Res[0]
###
# Session handling

# config
Server="127.0.0.1"
Port=25700

DBServ="localhost"
ProcServ="localhost"

Conns = dict()
#id:{username,password,info,infobase,lastip,lastagent}
def T9exec(*params):
    try:
        Conn=reconnect(Server, Port, Conns[params[0]]["info"])
    except:
        info = Conns[params[0]]["info"]
        Conn = connect(Server, Port, ProxyService, ProxyGUID,
                       info, str(params[0]),
                       Conns[params[0]]["lastip"], Conns[params[0]]["lastagent"])
        login(Conn[0], ProcServ, DBServ, Conns[params[0]]["infobase"],
              Conns[params[0]]["login"], Conns[params[0]]["password"], "")
        Conns[params[0]]["info"] = Conn[1]
    Res=xml_call(Conn[0], params[1], params[2:])[0]
    standby(Conn[0])
    return Res


def T9login(infobase, username, password, RemoteIp, UserAgent):
    if isinstance(infobase, unicode):
        infobase = infobase.encode('1251')
    if isinstance(username, unicode):
        username = username.encode('1251')
    if isinstance(password, unicode):
        password = password.encode('1251')
    nextSID = len(Conns) + 1
    while nextSID in Conns:
        nextSID += 1
    (Sock, info) = connect(Server, Port, ProxyService, ProxyGUID, None,
                        str(nextSID), RemoteIp, UserAgent)
    login(Sock, ProcServ, DBServ, infobase, username, password, "")
    Conns[nextSID] = {"username": username,
                      "password": password,
                      "info": info,
                      'lastip': RemoteIp,
                      'lastagent': UserAgent,
                      'infobase': infobase}
    standby(Sock)
    return nextSID

def T9drop(logid):
    try:
        Conn=reconnect(Server, Port, Conns[logid]["info"])
    except:
        return ""
    if Conn<>None:
        disconnect(Conn[0])
    return ""


class T9disp():
    def _dispatch(self,method,params):
        if method[:3]=="T9.":
            return T9exec(params[0],method[3:], *params[1:])

if __name__ == "__main__":
    from SimpleXMLRPCServer import SimpleXMLRPCServer
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

    # Restrict to a particular path.
    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

        def _dispatch(self, method, params):
            if method == 'T9login':
                params = list(params)
                if len(params) < 4:
                    params.append(self.client_address[0])
                if len(params) < 5:
                    params.append(self.headers['user-agent'])
            return SimpleXMLRPCServer._dispatch(self.server, method, params)

    # Create server
    server = SimpleXMLRPCServer(("localhost", 8001),
                            requestHandler=RequestHandler,
                            encoding="windows-1251")

    server.register_function(T9login)
    server.register_function(T9exec)
    server.register_function(T9drop)
    server.register_introspection_functions()
    T9disp1 = T9disp()
    server.register_instance(T9disp1, True)

    server.serve_forever()
