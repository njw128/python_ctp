#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'HaiFeng'
__mtime__ = '2016/9/13'
"""
import sys
import os
import platform
sys.path.append(os.path.join(sys.path[0], '..'))  # 调用父目录下的模块

import py_ctp.ctp_struct as ctp
from py_ctp.ctp_quote import Quote
from py_ctp.ctp_trade import Trade
import _thread
from time import sleep


class Test:

    def __init__(self):
        self.Session = ''
        dllpath = os.path.join(os.path.split(os.path.realpath(__file__))[0], '..', 'dll')
        # 初始化行情类和交易类
        self.q = Quote(os.path.join(dllpath, 'ctp_quote.' + ('dll' if 'Windows' in platform.system() else 'so')))
        self.t = Trade(os.path.join(dllpath, 'ctp_trade.' + ('dll' if 'Windows' in platform.system() else 'so')))
        self.req = 0
        self.ordered = False
        self.needAuth = False
        self.RelogEnable = True

        # 行情前置连接
    def q_OnFrontConnected(self):
        print('connected')
        # 行情-用户登陆请求
        self.q.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd)

        # 行情-登陆响应
    def q_OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info)
        # 订阅行情
        self.q.SubscribeMarketData('pb1811')
        self.q.SubscribeMarketData('ni1811')
        # self.q.SubscribeMarketData('rb1812')
        # self.q.SubscribeMarketData('ni1811')
        self.q.SubscribeMarketData('rb1810')



    def q_OnTick(self, tick: ctp.CThostFtdcMarketDataField):
        print("----enter q_OnTick---------",tick.getUpdateTime(),tick.getInstrumentID(),tick.getLastPrice())
        f = tick
        # print(tick)

        if not self.ordered:
            _thread.start_new_thread(self.Order, (f,))
            self.ordered = True

    # 报单
    def Order(self, f: ctp.CThostFtdcMarketDataField):
        print("报单","-----enter Order------------")
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
            VolumeTotalOriginal=1,
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

    # 交易接口-登陆
    def OnFrontConnected(self):
        if not self.RelogEnable:
            return
        print('connected',"---------enter OnFrontConnected------------")
        if self.needAuth:
            self.t.ReqAuthenticate(self.broker, self.investor, '@haifeng', '8MTL59FK1QGLKQW2')
        else:
            print("1-------------")
            self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd, UserProductInfo='@mingxi')

    def OnFrontDisconnected(self, reason: int):
        print(reason)

    def OnRspAuthenticate(self, pRspAuthenticateField: ctp.CThostFtdcRspAuthenticateField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print('auth：{0}:{1}'.format(pRspInfo.getErrorID(), pRspInfo.getErrorMsg()))
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd, UserProductInfo='@haifeng')

    # 交易接口-登陆响应
    def OnRspUserLogin(self, rsp: ctp.CThostFtdcRspUserLoginField, info: ctp.CThostFtdcRspInfoField, req: int, last: bool):
        print(info.getErrorMsg(),"-------enter OnRspUserLogin--------")

        if info.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            # 交易接口-投资者结算结果确认
            self.t.ReqSettlementInfoConfirm(BrokerID=self.broker, InvestorID=self.investor)
        else:
            self.RelogEnable = False

        # 交易接口-投资者结算结果确认应答
    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm: ctp.CThostFtdcSettlementInfoConfirmField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        # print(pSettlementInfoConfirm)
        _thread.start_new_thread(self.StartQuote, ())

        # 开启行情
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
        self.q.RegisterFront(self.frontAddr.split(',')[1])
        # 连接运行
        self.q.Init()
        # self.q.Join()

    def Qry(self):
        sleep(1.1)
        # 请求查询合约
        self.t.ReqQryInstrument()
        while True:
            sleep(1.1)
            # 请求查询资金账户
            self.t.ReqQryTradingAccount(self.broker, self.investor)
            sleep(1.1)
            # 持仓查询请求
            self.t.ReqQryInvestorPosition(self.broker, self.investor)
            return

    def OnRtnInstrumentStatus(self, pInstrumentStatus: ctp.CThostFtdcInstrumentStatusField):
        print(pInstrumentStatus.getInstrumentStatus())

        # 报单录入应答
    def OnRspOrderInsert(self, pInputOrder: ctp.CThostFtdcInputOrderField, pRspInfo: ctp.CThostFtdcRspInfoField, nRequestID: int, bIsLast: bool):
        print("---------报单应答---------")
        print(pRspInfo)
        print(pInputOrder)
        print(pRspInfo.getErrorMsg())

        # 报单回报
    def OnRtnOrder(self, pOrder: ctp.CThostFtdcOrderField):
        print("------OnRtnOrder----------")
        print(pOrder)
        if pOrder.getSessionID() == self.Session and pOrder.getOrderStatus() == ctp.OrderStatusType.NoTradeQueueing:
            print("撤单")
            self.t.ReqOrderAction(
                self.broker, self.investor,
                InstrumentID=pOrder.getInstrumentID(),
                OrderRef=pOrder.getOrderRef(),
                FrontID=pOrder.getFrontID(),
                SessionID=pOrder.getSessionID(),
                ActionFlag=ctp.ActionFlagType.Delete)

    def Run(self):
        # CreateApi时会用到log目录,需要在程序目录下创建**而非dll下**
        self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)

        self.t.OnFrontConnected = self.OnFrontConnected
        self.t.OnFrontDisconnected = self.OnFrontDisconnected
        self.t.OnRspUserLogin = self.OnRspUserLogin
        self.t.OnRspSettlementInfoConfirm = self.OnRspSettlementInfoConfirm
        self.t.OnRspAuthenticate = self.OnRspAuthenticate
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnRspOrderInsert = self.OnRspOrderInsert
        self.t.OnRtnOrder = self.OnRtnOrder
        # _thread.start_new_thread(self.Qry, ())
        self.t.RegCB()

        self.frontAddr = 'tcp://180.168.146.187:10000,tcp://180.168.146.187:10010'
        # self.frontAddr = 'tcp://180.168.146.187:10030,tcp://180.168.146.187:10031'
        self.broker = '9999'
        self.investor = '118513'
        self.pwd = 'mingxi602603'
        self.t.RegisterFront(self.frontAddr.split(',')[0])
        self.t.SubscribePrivateTopic(nResumeType=2)  # quick
        self.t.SubscribePrivateTopic(nResumeType=2)
        self.t.Init()
        # self.t.Join()


if __name__ == '__main__':
    t = Test()
    t.Run()
    input()
    t.t.Release()
    input()
