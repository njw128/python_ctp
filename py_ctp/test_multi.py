#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import platform
sys.path.append(os.path.join(sys.path[0], '..'))  # 调用父目录下的模块

import py_ctp.ctp_struct as ctp
from py_ctp.ctp_quote import Quote
from py_ctp.ctp_trade import Trade
import _thread
from time import sleep
import csv,json,threading,time
from queue import Queue
from apscheduler.schedulers.blocking import BlockingScheduler


TraderAddress=""
MaketAddress=""
Broker=""
UserAccount=""
Passwd=""
OrderDict={}  #保存每个合约的初始信息 key:future value:futureModel
traderDict={}  #保存每个合约交易的信息
endFlag=False  #标志每个合约是否交易结束
future_queue=Queue()
future_list=[]
scheduler = BlockingScheduler()


class FutureModel(object):
    def __init__(self):
        self.code=""
        self.volume=""
        self.direction=""
        self.lastPrice=""
        self.deal=0
        self.remain=""
        self.attr=""

def initSchedule():
    global OrderDict,TraderAddress,MaketAddress,Broker,UserAccount,Passwd
    with open("config.json", 'r') as f:
        config_json = json.loads(f.read())
        TraderAddress=config_json['traderFront']
        MaketAddress=config_json['maketFront']
        Broker=config_json['broker']
        UserAccount = config_json['user']
        Passwd = config_json['passwd']

    if TraderAddress=="":
        print("traderFront is null")
        return
    if MaketAddress=="":
        print("maketFront is null")
        return
    if Broker=="":
        print("broker is null")
        return
    if UserAccount=="":
        print("user is null")
        return
    if Passwd=="":
        print("passwd is null")
        return

    with open("orderBook.csv", 'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            code = row[0]
            volume=row[1]
            # 0-卖出 1-买入
            direction=0
            if int(volume)>0:
                direction=1
            futureModel=FutureModel()
            futureModel.code=code
            futureModel.volume=volume
            futureModel.remain=volume
            futureModel.direction=direction
            OrderDict[code]=futureModel


class Quoter:
    def __init__(self,address,broker,investor,passwd):
        self.Session = ''
        dllpath = os.path.join(os.path.split(os.path.realpath(__file__))[0], '..', 'dll')
        self.q = Quote(os.path.join(dllpath, 'ctp_quote.' + ('dll' if 'Windows' in platform.system() else 'so')))
        self.address=address
        self.broker=broker
        self.investor=investor
        self.pwd=passwd


    def q_OnFrontConnected(self):
        print('connected',"---------enter q_OnFrontConnected-----------")
        # 行情-用户登陆请求
        self.q.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd)


    def q_OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info,"------enter q_OnRspUserLogin--------")
        for temp_future in OrderDict.keys():
            self.q.SubscribeMarketData(temp_future)


    def q_OnTick(self, tick: ctp.CThostFtdcMarketDataField):
        print("----enter q_OnTick---------",tick.getUpdateTime(),tick.getInstrumentID(),tick.getLastPrice())
        instrustmentId=tick.getInstrumentID()
        OrderDict[instrustmentId].lastPrice=tick.getLastPrice()
        OrderDict[instrustmentId].attr = tick
        print(OrderDict[instrustmentId].lastPrice)


    def StartQuote(self):
        print("----------enter StartQuote-----------")
        # 初始化行情线程，new api,new spi,spi注册api,
        self.q.CreateApi()
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)

        self.q.OnFrontConnected = self.q_OnFrontConnected
        self.q.OnRspUserLogin = self.q_OnRspUserLogin
        self.q.OnRtnDepthMarketData = self.q_OnTick

        self.q.RegCB()

        # 设置行情前置地址
        self.q.RegisterFront(self.address)
        # 连接运行
        self.q.Init()
        
        
class Trader:
    def __init__(self,address,broker,investor,passwd):
        self.Session = ''
        dllpath = os.path.join(os.path.split(os.path.realpath(__file__))[0], '..', 'dll')
        self.t = Trade(os.path.join(dllpath, 'ctp_trade.' + ('dll' if 'Windows' in platform.system() else 'so')))
        self.address=address
        self.broker=broker
        self.investor=investor
        self.pwd=passwd
        self.RelogEnable=True
        self.req=0


    def OnFrontConnected(self):
        if not self.RelogEnable:
            return
        print('connected',"-------------enter OnFrontConnected -----------")
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd,UserProductInfo='@haifeng')

    def OnRspAuthenticate(self, pRspAuthenticateField: ctp.CThostFtdcRspAuthenticateField,
                              pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print('auth：{0}:{1}'.format(pRspInfo.getErrorID(), pRspInfo.getErrorMsg()))
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd,
                                UserProductInfo='@haifeng')

        # 交易接口-登陆响应
    def OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int,
                           last: bool):
        print(info.getErrorMsg(), "-------enter OnRspUserLogin--------")

        if info.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            # 交易接口-投资者结算结果确认
            self.t.ReqSettlementInfoConfirm(BrokerID=self.broker, InvestorID=self.investor)
        else:
            self.RelogEnable = False

    # 交易接口-投资者结算结果确认应答
    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm: ctp.CThostFtdcSettlementInfoConfirmField,
                                       pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
            print(pSettlementInfoConfirm,"-------------enter OnRspSettlementInfoConfirm------------------")
            # _thread.start_new_thread(self.StartQuote, ())

    def OnRtnInstrumentStatus(self, pInstrumentStatus: ctp.CThostFtdcInstrumentStatusField):
        print(pInstrumentStatus.getInstrumentStatus(),"---------enter OnRtnInstrumentStatus-------------")

    # 报单录入应答
    def OnRspOrderInsert(self, pInputOrder: ctp.CThostFtdcInputOrderField, pRspInfo: ctp.CThostFtdcRspInfoField,
                         nRequestID: int, bIsLast: bool):
        print("---------报单应答---------")
        print(pRspInfo)
        print(pInputOrder)
        print(pRspInfo.getErrorMsg())

    #请求查询资金账户
    def ReqQryTradingAccount(self):
        print("---------enter ReqQryTradingAccount----------")
        self.t.ReqQryTradingAccount(self.broker,self.investor)

    #资金回报
    def OnRspQryTradingAccount(self, pTradingAccount: ctp.CThostFtdcTradingAccountField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print("--------enter OnRspQryTradingAccount--------")
        print('OnRspQryTradingAccount:, pTradingAccount: CThostFtdcTradingAccountField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        print(pTradingAccount)
        print(pRspInfo)
        print(nRequestID)
        print(bIsLast)

    # 持仓查询请求
    def ReqQryInvestorPosition(self):
        print("-------ReqQryInvestorPosition----------")
        self.t.ReqQryInvestorPosition(self.broker,self.investor)

    #持仓回报
    def OnRspQryInvestorPosition(self, pInvestorPosition: ctp.CThostFtdcInvestorPositionField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print("----------OnRspQryInvestorPosition-----------")
        print('OnRspQryInvestorPosition:, pInvestorPosition: CThostFtdcInvestorPositionField, pRspInfo: CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool')
        print(pInvestorPosition)
        print(pRspInfo)
        print(nRequestID)
        print(bIsLast)

    # 报单回报
    def OnRtnOrder(self, pOrder: ctp.CThostFtdcOrderField):
        print("------OnRtnOrder----------")
        print(pOrder)
        # 合约
        instrumentId = pOrder.getInstrumentID()
        # 订单状态
        orderStatus = pOrder.getOrderStatus()
        # 成交数量
        traderVolume = pOrder.getVolumeTraded()
        # 剩余数量
        remainVolume = pOrder.getVolumeTotal()
        # 将每次返回的报单回报保存在traderDict
        traderDict[instrumentId] = pOrder
        # 如果全部成交完，从剩余中减去成交量
        OrderDict[instrumentId]=pOrder
        if orderStatus==ctp.OrderStatusType.AllTraded or orderStatus==ctp.OrderStatusType.PartTradedNotQueueing and orderStatus==ctp.OrderStatusType.Canceled:
            OrderDict[instrumentId].remain=int(OrderDict[instrumentId].remain)-traderVolume
            del traderDict[instrumentId]
        if len(traderDict.keys())==0:
            batchInsertOrder(self)


    def cancelAction(self, pOrder: ctp.CThostFtdcOrderField):
        print("撤单")
        if pOrder.getSessionID() == self.Session and pOrder.getOrderStatus() == ctp.OrderStatusType.NoTradeQueueing:
            self.t.ReqOrderAction(
                self.broker, self.investor,
                InstrumentID=pOrder.getInstrumentID(),
                OrderRef=pOrder.getOrderRef(),
                FrontID=pOrder.getFrontID(),
                SessionID=pOrder.getSessionID(),
                ActionFlag=ctp.ActionFlagType.Delete)

        # 报单
    def Order(self, f: ctp.CThostFtdcMarketDataField,needVolume):
        print("报单", "-----enter Order------------")
        self.req += 1
        self.t.ReqOrderInsert(
            BrokerID=self.broker,
            InvestorID=self.investor,
            InstrumentID=f.getInstrumentID(),
            OrderRef='{0:>12}'.format(self.req),
            UserID=self.investor,
            OrderPriceType=ctp.OrderPriceTypeType.LimitPrice,
            Direction=ctp.DirectionType.Buy,
            CombOffsetFlag=ctp.OffsetFlagType.Open.__char__(),
            CombHedgeFlag=ctp.HedgeFlagType.Speculation.__char__(),
            # LimitPrice=f.getLastPrice() - 50,
            LimitPrice=f.getLastPrice(),
            VolumeTotalOriginal=needVolume,
            TimeCondition=ctp.TimeConditionType.GFD,
            # GTDDate=''
            VolumeCondition=ctp.VolumeConditionType.AV,
            MinVolume=1,
            ContingentCondition=ctp.ContingentConditionType.Immediately,
            StopPrice=0,
            ForceCloseReason=ctp.ForceCloseReasonType.NotForceClose,
            IsAutoSuspend=0,
            IsSwapOrder=0,
            UserForceClose=0)

    def Run(self):
        # CreateApi时会用到log目录,需要在程序目录下创建**而非dll下**
        self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)

        self.t.OnFrontConnected = self.OnFrontConnected
        self.t.OnFrontDisconnected = self.OnFrontConnected
        self.t.OnRspUserLogin = self.OnRspUserLogin
        self.t.OnRspSettlementInfoConfirm = self.OnRspSettlementInfoConfirm
        self.t.OnRspAuthenticate = self.OnRspAuthenticate
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnRspOrderInsert = self.OnRspOrderInsert
        self.t.OnRtnOrder = self.OnRtnOrder
        self.t.OnRspQryInvestorPosition=self.OnRspQryInvestorPosition
        self.t.OnRspQryTradingAccount=self.OnRspQryTradingAccount
        # _thread.start_new_thread(self.Qry, ())
        self.t.RegCB()
        self.t.RegisterFront(self.address)
        self.t.SubscribePrivateTopic(nResumeType=2)  # quick
        self.t.SubscribePrivateTopic(nResumeType=2)
        self.t.Init()



def batchInsertOrder(trader:Trader):
    print("------batchInsertOrder-----")
    #如果trderDict中的报单反馈没有处理完，不能进行再次报单
    if len(traderDict.keys())>0:
        return
    if endFlag:
        return
    for key,value in OrderDict.items():
        remainVolume = int(value.remain)
        attr=value.attr
        if remainVolume>0 and attr!="":
            trader.Order(attr,remainVolume)


def batchCancelOrder(trader:Trader):
    judgeTraderOver()
    if len(traderDict.keys())==0:
        return
    for key,value in traderDict.items():
        trader.cancelAction(value)


def judgeTraderOver():
    global endFlag
    for key,value in OrderDict.items():
        remainVolume=int(value.remain)
        if remainVolume>0:
            return
    endFlag=True
    stopBuyAll()

def stopBuyAll():
    global endFlag
    if endFlag:
        scheduler.remove_all_jobs()
        scheduler.shutdown(wait=False)





if __name__ == '__main__':
    initSchedule()
    print(UserAccount)

    print(Passwd)
    print(OrderDict)

    # 实例化行情接口
    quoter=Quoter(MaketAddress,Broker,UserAccount,Passwd)
    # 启动行情
    _thread.start_new_thread(quoter.StartQuote,())
    # input()
    #判断每个合约的行情是否有回复
    maketInfoFlag = True
    while maketInfoFlag:
        nullFlag = 0
        for key,value in OrderDict.items():
            maketInfo=value.attr
            if maketInfo=="":
                nullFlag=1
                break
            else:
                # maketInfo=ctp.CThostFtdcMarketDataField(maketInfo)
                print(key,maketInfo.getInstrumentID(),maketInfo.getUpdateTime(),maketInfo.getLastPrice())
        if nullFlag==0:
            maketInfoFlag=False
        time.sleep(5)
    print(OrderDict)
    # 实例化交易接口
    trader = Trader(TraderAddress, Broker, UserAccount, Passwd)
    trader.Run()
    batchInsertOrder(trader)
    scheduler.add_job(func=batchCancelOrder,args=(trader,),trigger='interval',seconds=5)
    scheduler.start()




    # input()
