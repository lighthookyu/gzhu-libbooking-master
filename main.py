import json
import requests
import re
import execjs
from lxml import html
import datetime
import sys
import schedule
import time


def get_rsa(un, psd, lt):
    js_res = requests.get('https://newcas.gzhu.edu.cn/cas/comm/js/des.js')
    context = execjs.compile(js_res.text)
    result = context.call("strEnc", un + psd + lt, '1', '2', '3')
    return result


class GZHU(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.client = requests.session()
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        })
        self.url = {
            'root': 'http://libbooking.gzhu.edu.cn/',
            'user_info': 'http://libbooking.gzhu.edu.cn/ic-web/auth/userInfo',
            'auth': 'http://libbooking.gzhu.edu.cn/ic-web/auth/address?finalAddress=http://libbooking.gzhu.edu.cn/#/ic/home&errPageUrl=http://libbooking.gzhu.edu.cn/#/error&manager=false&consoleType=16',
            'lan_list': 'http://libbooking.gzhu.edu.cn/ic-web/Language/getLanList',
            '101': 'http://libbooking.gzhu.edu.cn/ic-web/reserve?roomIds=100647013&resvDates=20220416&sysKind=8',
            '103': 'http://libbooking.gzhu.edu.cn/ic-web/reserve?roomIds=100647014&resvDates=20220416&sysKind=8',
        }

    def login(self):
        new_cas_url = 'https://newcas.gzhu.edu.cn/cas/login'
        res = self.client.get(new_cas_url)
        lt = re.findall(r'name="lt" value="(.*)"', res.text)

        login_form = {
            'rsa': get_rsa(self.username, self.password, lt[0]),
            'ul': len(self.username),
            'pl': len(self.password),
            'lt': lt[0],
            'execution': 'e1s1',
            '_eventId': 'submit',
        }

        resp = self.client.post(new_cas_url, data=login_form, )
        selector = html.fromstring(resp.text)
        if selector.xpath('//title/text()')[0] == '融合门户':
            return True
        else:
            return False

    def loginLib(self, select_room):
        """
        :param select_room: '101’ or '103'
        :return:
        """
        self.client.headers.update({
            'Referer': 'http://libbooking.gzhu.edu.cn/',
            'Host': 'libbooking.gzhuedu.cn'
        })
        r1 = self.client.get(self.url['auth'])
        uuid = re.findall(r'uuid%3D(.*)%26console', r1.text)
        self.url.update({
            '302pages': 'http://libbooking.gzhu.edu.cn/authcenter/toLoginPage?'
                        'redirectUrl=http%3A%2F%2Flibbooking.gzhu.edu.cn%2Fic-'
                        'web%2F%2Fauth%2Ftoken%3Fmanager%3Dfalse%26uuid%3D{uuid}'
                        '%26consoleType%3D16&extInfo='.format(uuid=uuid[0])
        })
        if self.login():
            r2 = self.client.get(self.url['302pages'])
            if 'Please enable it to continue.' not in r2.text:
                with open('error.log', 'w') as fp:
                    fp.write(r2.text)
                print('自习室系统登录失败,最后一个请求的文本写入error.log')
                sys.exit(2)
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
        the_day_after_tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=2),
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


# 云函数使用这行
# start()
# 本地挂脚本
schedule.every().day.at("06:16").do(start)
while True:
    schedule.run_pending()
    time.sleep(5)
