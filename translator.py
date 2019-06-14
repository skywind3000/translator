#! /usr/bin/env python
# -*- coding: utf-8 -*-
#======================================================================
#
# translator.py - 命令行翻译（谷歌，必应，百度，有道，词霸）
#
# Created by skywind on 2019/06/14
# Last Modified: 2019/06/14 16:05:47
#
#======================================================================
from __future__ import print_function, unicode_literals
import sys
import time
import os
import random
import copy


#----------------------------------------------------------------------
# BasicTranslator
#----------------------------------------------------------------------
class BasicTranslator(object):

    def __init__ (self, name, **argv):
        self._name = name
        self._config = {}  
        self._options = argv
        self._session = None
        self._agent = None
        self._load_config(name)
        self._check_proxy()

    def __load_ini (self, ininame, codec = None):
        config = {}
        if not ininame:
            return None
        elif not os.path.exists(ininame):
            return None
        try:
            content = open(ininame, 'rb').read()
        except IOError:
            content = b''
        if content[:3] == b'\xef\xbb\xbf':
            text = content[3:].decode('utf-8')
        elif codec is not None:
            text = content.decode(codec, 'ignore')
        else:
            codec = sys.getdefaultencoding()
            text = None
            for name in [codec, 'gbk', 'utf-8']:
                try:
                    text = content.decode(name)
                    break
                except:
                    pass
            if text is None:
                text = content.decode('utf-8', 'ignore')
        if sys.version_info[0] < 3:
            import StringIO
            import ConfigParser
            sio = StringIO.StringIO(text)
            cp = ConfigParser.ConfigParser()
            cp.readfp(sio)
        else:
            import configparser
            cp = configparser.ConfigParser(interpolation = None)
            cp.read_string(text)
        for sect in cp.sections():
            for key, val in cp.items(sect):
                lowsect, lowkey = sect.lower(), key.lower()
                config.setdefault(lowsect, {})[lowkey] = val
        if 'default' not in self.config:
            config['default'] = {}
        return config

    def _load_config (self, name):
        self._config = {}
        ininame = os.path.expanduser('~/.config/translator/config.ini')
        config = self.__load_ini(ininame)
        if not config:
            return False
        for section in ('default', name):
            items = config.get(section, {})
            for key in items:
                self._config[key] = items[key]
        return True

    def _check_proxy (self):
        proxy = os.environ.get('all_proxy', None)
        if not proxy:
            return False
        if not isinstance(proxy, str):
            return False
        if 'proxy' not in self._config:
            self._config['proxy'] = proxy.strip()
        return True

    def request (self, url, data = None, post = False, header = None):
        import requests
        if not self._session:
            self._session = requests.Session()
        argv = {}
        if header is not None:
            header = copy.deepcopy(header)
        else:
            header = {}
        if self._agent:
            header['User-Agent'] = self._agent
        argv['headers'] = header
        timeout = self._config.get('timeout', 7)
        proxy = self._config.get('proxy', None)
        if timeout:
            argv['timeout'] = float(timeout)
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
            argv['proxies'] = proxies
        if not post:
            if data is not None:
                argv['params'] = data
        else:
            if data is not None:
                argv['data'] = data
        if not post:
            r = self._session.get(url, **argv)
        else:
            r = self._session.post(url, **argv)
        return r

    def http_get (self, url, data = None, header = None):
        return self.request(url, data, False, header)

    def http_post (self, url, data = None, header = None):
        return self.request(url, data, True, header)

    def url_unquote (self, text, plus = True):
        if sys.version_info[0] < 3:
            import urllib
            if plus:
                return urllib.unquote_plus(text)
            return urllib.unquote(text)
        import urllib.parse
        if plus:
            return urllib.parse.unquote_plus(text)
        return urllib.parse.unquote(text)

    def url_quote (self, text, plus = True):
        if sys.version_info[0] < 3:
            import urllib
            if plus:
                return urllib.quote_plus(text)
            return urlparse.quote(text)
        import urllib.parse
        if plus:
            return urllib.parse.quote_plus(text)
        return urllib.parse.quote(text)

    # 翻译结果：需要填充如下字段
    def translate (self, sl, tl, text):
        res = {}
        res['sl'] = sl              # 来源语言
        res['tl'] = sl              # 目标语言
        res['text'] = text          # 需要翻译的文本
        res['translation'] = None   # 翻译结果
        res['html'] = None          # HTML 格式的翻译结果（如果有的话）
        res['info'] = None          # 原始网站的返回值
        return res

    # 是否是英文
    def check_english (self, text):
        for ch in text:
            if ord(ch) >= 128:
                return False
        return True

    # 猜测语言
    def guess_language (self, text):
        if self.check_english(text):
            return ('en-US', 'zh-CN')
        return ('zh-CN', 'en-US')
    

#----------------------------------------------------------------------
# Google Translator
#----------------------------------------------------------------------
class GoogleTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(GoogleTranslator, self).__init__('google', **argv)
        self._agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0)'
        self._agent += ' Gecko/20100101 Firefox/59.0'

    def get_url (self, sl, tl, qry):
        http_host = self._options.get('host', 'translate.googleapis.com')
        http_host = 'translate.google.cn'
        qry = self.url_quote(qry)
        url = 'https://{}/translate_a/single?client=gtx&sl={}&tl={}&dt=at&dt=bd&dt=ex&' \
              'dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&q={}'.format(
                      http_host, sl, tl, qry)
        return url

    def translate (self, sl, tl, text):
        if (sl is None or sl == 'auto') and (tl is None or tl == 'auto'):
            sl, tl = self.guess_language(text)
        self.text = text
        url = self.get_url(sl, tl, text)
        r = self.http_get(url)
        obj = r.json()
        res = {}
        res['sl'] = obj[2] and obj[2] or sl
        res['tl'] = obj[1] and obj[1] or tl
        res['info'] = obj
        res['translation'] = self.render(obj)
        res['html'] = None
        return res

    def render (self, obj):
        result = self.get_result('', obj)
        result = self.get_synonym(result, obj)
        if len(obj) >= 13 and obj[12]:
            result = self.get_definitions(result, obj)
        return result

    def get_result (self, result, obj):
        for x in obj[0]:
            if x[0]:
                result += x[0]
        return result

    def get_synonym (self, result, resp):
        if resp[1]:
            result += '\n=========\n'
            result += 'Translations:\n'
            for x in resp[1]:
                result += '{}.\n'.format(x[0][0])
                for i in x[2]:
                    result += '{}: {}\n'.format(i[0], ", ".join(i[1]))
        return result

    def get_definitions (self, result, resp):
        result += '\n=========\n'
        result += '0_0: Definitions of {}\n'.format(self.text)
        for x in resp[12]:
            result += '{}.\n'.format(x[0])
            for y in x[1]:
                result += '  - {}\n'.format(y[0])
                result += '    * {}\n'.format(y[2]) if len(y) >= 3 else ''
        return result



#----------------------------------------------------------------------
# Youdao Translator
#----------------------------------------------------------------------
class YoudaoTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(YoudaoTranslator, self).__init__('youdao', **argv)
        self.url = 'https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule'
        self.D = "ebSeFb%=XZ%T[KZ)c(sy!"

    def get_md5 (self, value):
        import hashlib
        m = hashlib.md5()
        # m.update(value)
        m.update(value.encode('utf-8'))
        return m.hexdigest()

    def sign (self, text, salt):
        s = "fanyideskweb" + text + salt + self.D
        return self.get_md5(s)

    def translate (self, sl, tl, text):
        if (sl is None or sl == 'auto') and (tl is None or tl == 'auto'):
            sl, tl = self.guess_language(text)
        self.text = text
        salt = str(int(time.time() * 1000) + random.randint(0, 10))
        sign = self.sign(text, salt)
        header = {
            'Cookie': 'OUTFOX_SEARCH_USER_ID=-2022895048@10.168.8.76;',
            'Referer': 'http://fanyi.youdao.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        data = {
            'i': text,
            'from': sl,
            'to': tl, 
            'smartresult': 'dict',
            'client': 'fanyideskweb',
            'salt': salt,
            'sign': sign,
            'doctype': 'json',
            'version': '2.1',
            'keyfrom': 'fanyi.web',
            'action': 'FY_BY_CL1CKBUTTON',
            'typoResult': 'true'
        }
        r = self.http_post(self.url, data, header)
        obj = r.json()
        translation = ''
        result = obj.get('translateResult', [])
        return obj


#----------------------------------------------------------------------
# Baidu Translator
#----------------------------------------------------------------------
class BaiduTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(BaiduTranslator, self).__init__('baidu', **argv)
        self._agent = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
        self._agent += ' AppleWebKit/537.36 (KHTML, like Gecko) '
        self._agent += ' Chrome/46.0.2490.76 Mobile Safari/537.36'
        langmap = {}
        langmap['zh-CN'] = 'zh'
        langmap['en-US'] = 'en'
        self._langmap = langmap

    def translate (self, sl, tl, text):
        if (sl is None or sl == 'auto') and (tl is None or tl == 'auto'):
            sl, tl = self.guess_language(text)
        req = {}
        req['query'] = text
        req['from'] = self._langmap.get(sl, 'en')
        req['to'] = self._langmap.get(tl, 'en')
        url = "https://fanyi.baidu.com/extendtrans"
        r = self.http_post(url, req)
        return r


#----------------------------------------------------------------------
# testing suit
#----------------------------------------------------------------------
if __name__ == '__main__':
    def test1():
        bt = BasicTranslator('test')
        r = bt.request("http://www.baidu.com")
        print(r.text)
        return 0
    def test2():
        gt = GoogleTranslator()
        r = gt.translate('auto', 'auto', 'Hello, World !!')
        # r = gt.translate('auto', 'auto', '你吃饭了没有?')
        # r = gt.translate('auto', 'auto', 'kiss')
        # r = gt.translate('auto', 'auto', '亲吻')
        import pprint
        print(r['translation'])
        pprint.pprint(r['info'])
        return 0
    def test3():
        t = YoudaoTranslator()
        r = t.translate('auto', 'auto', 'kiss')
        import pprint
        pprint.pprint(r)
        return 0
    test2()



