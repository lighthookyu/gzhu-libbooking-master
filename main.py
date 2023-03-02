# -*- coding: utf8 -*-
import json
import requests
import datetime
import base64
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pksc1_v1_5
from Crypto.PublicKey import RSA


def encrypt(password, public_key):
    rsakey = RSA.importKey(public_key)
    cipher = Cipher_pksc1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(password.encode()))
    return cipher_text.decode()


class GZHU(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.client = requests.session()
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        })
        self.url = {
            'scancode': 'http://libbooking.gzhu.edu.cn/scancode.html#/login?sta=1&sysid=1EW&lab=69&type=1',
            'user_info': 'http://libbooking.gzhu.edu.cn/ic-web/auth/userInfo',
            '101': 'http://libbooking.gzhu.edu.cn/ic-web/reserve?roomIds=100647013&resvDates=20220416&sysKind=8',
            '103': 'http://libbooking.gzhu.edu.cn/ic-web/reserve?roomIds=100647014&resvDates=20220416&sysKind=8',
        }

    def loginLib(self, select_room):
        """
        :param select_room: '101’ or '103'
        :return:
        """
        self.client.headers.update({
            'Referer': 'http://libbooking.gzhu.edu.cn/',
            'Host': 'libbooking.gzhuedu.cn'
        })

        # 获得publicKey
        r1 = self.client.get('http://libbooking.gzhu.edu.cn/ic-web/login/publicKey')
        key = json.loads(r1.text)['data']
        publicKey = key['publicKey']
        nonceStr = key['nonceStr']
        psd = '{};{}'.format(self.password, nonceStr)
        print(r1)

        public_key = '-----BEGIN PUBLIC KEY-----\n' + publicKey + '\n-----END PUBLIC KEY-----'
        password = encrypt(psd, public_key)
        print('password:', password)

        login_data = {
           "bind": 0,
           "logonName": self.username,
           "password": password,
           "type": "",
           "unionId": ""
        }
        self.client.post('http://libbooking.gzhu.edu.cn/ic-web/phoneSeatReserve/login', json=login_data)
        r3 = self.client.get(self.url['user_info'])
        data = json.loads(r3.text)
        if data['message'] == '查询成功':
            self.client.headers.update({
                'token': data['data']['token']
            })
            print('自习室系统登录成功')
            r4 = self.client.get(self.url[select_room])
            room_data = json.loads(r4.text)
            return room_data, data['data']['accNo']

    def postReserve(self, acc_no, begin_time, end_time, dev_id):
        """
        :param acc_no: 自习室系统识别用户的id，int,len=9
        :param begin_time: 开始时间,str,  '1970-01-01 00:00:00'
        :param end_time: 结束时间,str,  '1970-01-01 00:00:00'
        :param dev_id: 座位id,str, len=9

        :return:
        """
        post_data = {
            "sysKind": 8,
            "appAccNo": acc_no,
            "memberKind": 1,
            "resvMember": [acc_no],
            "resvBeginTime": begin_time,
            "resvEndTime": end_time,
            "testName": "",
            "captcha": "",
            "resvProperty": 0,
            "resvDev": [int(dev_id)],
            "memo": ""
        }
        resp = self.client.post('http://libbooking.gzhu.edu.cn/ic-web/reserve', json=post_data)
        print(json.loads(resp.text)['message'])

    def reserve(self, acc_no, set_bt, set_et, dev_id):
        # 从后天修正为明天 2->1
        the_day_after_tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1),
                                                            '%Y-%m-%d')
        bt = '{} {}'.format(the_day_after_tomorrow, set_bt)
        et = '{} {}'.format(the_day_after_tomorrow, set_et)
        print('正在post数据，bt:{bt};et:{et}'.format(bt=bt, et=et))
        self.postReserve(acc_no=acc_no,
                         begin_time=bt,
                         end_time=et,
                         dev_id=dev_id)
        return


def start():
    with open('config.json', 'r') as fp:
        cfg = json.load(fp)
        g = GZHU(cfg['username'], cfg['password'])
        room_datas, accNo = g.loginLib(cfg['room'])
        for task in cfg['habit']:
            dev_id = ''
            for data in room_datas['data']:
                if data["devName"] == task['seat_id']:
                    dev_id = data["devId"]
                    break
            g.reserve(acc_no=accNo,
                      set_bt=task['bt'],
                      set_et=task['et'],
                      dev_id=dev_id)


def main_handler(event, context):
    start()
