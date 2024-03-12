import requests
import warnings
import re
import json
import os

from datetime import datetime, date
from collections import OrderedDict
from flask import Flask, jsonify,request
from bs4 import BeautifulSoup

# 关闭 Python 的警告输出
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 苹果官方查询定价网址，基于该网址进行解析
apple_url = 'https://support.apple.com/zh-cn/HT201238'

# fixer.io网站apikey，用于查询实时汇率


# 获取iCloud最新全球订阅价格
def get_icloud_latest_global_prices(capacity_size, formatted_date):

    response = requests.get(apple_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')


        # 获取最新全球汇率，基准货币因api限制，暂时使用欧元，内部统一转化为人民币计价
        # cny_exchange_rates = get_cny_exchange_rates(api_key=api_key, base_currency='EUR', use_local= use_local_config)
        cny_exchange_rates = get_exchange_rate(formatted_date)

        # 得到所有地区价格
        country_prices = get_country_prices(soup, cny_exchange_rates, capacity_size)
        return country_prices
    else:
        print("Failed to fetch data from the website.")
        return None


def get_country_prices(soup, exchange_rates, capacity_size):
    # 获取所有地区 块
    countries = get_all_country_block(soup)
    # print(countries)

    # 获取静态地区货币映射
    static_country_currencies = get_static_country_currencies()

    # 获取容量规格,默认2TB
    re_text = re.compile(r'2\s*(TB|GB)')
    if capacity_size == '50GB':
        re_text = re.compile(r'50\s*(TB|GB)')
    elif capacity_size == '200GB':
        re_text = re.compile(r'200\s*(TB|GB)')
    elif capacity_size == '2TB':
        re_text = re.compile(r'2\s*(TB|GB)')
    elif capacity_size == '6GB':
        re_text = re.compile(r'6\s*(TB|GB)')
    elif capacity_size == '12TB':
        re_text = re.compile(r'12\s*(TB|GB)')

    # 定义一个空字典来存储结果
    data = {}
    for row in countries:
        # 国家地区key
        country = get_n_string(row,1).split('（')[0]
        # 定位到2tb
        target_element = row.find('strong', text=re_text).next_sibling.strip()
        if len(target_element) < 3:
            print(country + '特殊解析')
            target_element = row.find('strong', text=re_text).next_sibling.next_sibling.next_sibling.strip()
        # 2TB 单价
        two_tb_unit_price = re.findall(r'\d+\.\d+|\d+',target_element)[0]
        # print( country + two_tb_unit_price)
        # print(exchange_rates[static_country_currencies[country]])

        # 判断是否使用美元，如果是直接使用美元计价
        # print(row)
        if "美元" in get_n_string(row,1):
            print(country + '不使用本国货币，使用usd')
            data[country] = float(exchange_rates['USD']) * float(two_tb_unit_price)
        elif '亚美尼亚' in row:
            data[country] = float(exchange_rates['USD']) * float(two_tb_unit_price)
        elif '冰岛' in row:
            data[country] = float(exchange_rates['USD']) * float(two_tb_unit_price)
        elif '阿尔巴尼亚' in row:
            data[country] = float(exchange_rates['USD']) * float(two_tb_unit_price)
        elif '白俄罗斯' in row:
            data[country] = float(exchange_rates['USD']) * float(two_tb_unit_price)
        elif '克罗地亚' in row:
            data[country] = float(exchange_rates['EUR']) * float(two_tb_unit_price)
        elif '中国大陆' in row:
            data[country] = float(two_tb_unit_price) * 1
        else:
            data[country] = float(exchange_rates[static_country_currencies[country]]) * float(two_tb_unit_price)

    # 按低到高排序
    sorted_lst = sorted(data.items(), key=lambda item: item[1])

    print(sorted_lst)
    return sorted_lst
 


# 获取第n个文本节点
def get_n_string(str, n):
    nth_text = None
    count = 0
    for string in str.stripped_strings:
        count += 1
        if count == n:
            nth_text = string
            break

    return nth_text


#获取所有地区元素块
def get_all_country_block(soup):
    # 找到包含关键元素的所有行
    p_elements = soup.find_all('p')
    # 存储结果的列表
    elements = []

    # 遍历所有 <p> 元素
    for p_element in p_elements:
        # 查找当前 <p> 元素的所有子元素中同时包含 <strong>2TB</strong> 和 <strong>12TB</strong> 的元素
        children_with_2TB = p_element.find_all('strong', text='2TB')
        children_with_2_TB = p_element.find_all('strong', text='2 TB')
        children_with_12TB = p_element.find_all('strong', text='12TB')
        
        # 如果同时找到 <strong>2TB</strong> 和 <strong>12TB</strong> 的元素，则将当前 <p> 元素添加到结果列表中
        if (children_with_2_TB or children_with_2TB) and children_with_12TB:
            elements.append(p_element)
    # print(elements)
    return elements


# 获取静态地区货币映射
STATIC_COUNTRY_CURRENCIES_FILE = 'static_country_currencies.json'
def get_static_country_currencies():
    # 检查文件是否存在并且包含所需日期的汇率数据
    if os.path.exists(STATIC_COUNTRY_CURRENCIES_FILE):
        with open(STATIC_COUNTRY_CURRENCIES_FILE, 'r') as file:
            return json.load(file)


# 定义汇率文件路径
RATE_FILE = 'exchange_rates.json'
def get_exchange_rate(date):
    # 检查文件是否存在并且包含所需日期的汇率数据
    if os.path.exists(RATE_FILE):
        with open(RATE_FILE, 'r') as file:
            rates = json.load(file)
            if date in rates:
                print('use_file')
                return rates[date]

    # 文件中不存在所需日期的汇率数据，进行实时查询
    rate = fetch_exchange_rate_from_api(date)
    
    # 保存汇率到文件
    if rate is not None:
        save_exchange_rate_to_file(date, rate)
    
    return rate


# 定义配置文件路径
CONFIG_FILE = 'config.json'
def get_config_value(key):
    # 检查文件是否存在并且包含所需日期的汇率数据
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            configs = json.load(file)
            if key in configs:
                return configs[key]


def fetch_exchange_rate_from_api(date):
    # 实时查询汇率的逻辑，这里使用示例API，你需要替换为你的实际API
    print('use_api')
    static_fixer_io_api_key = get_config_value('fixer_io_api_key')
    url = f"http://data.fixer.io/api/latest?access_key={static_fixer_io_api_key}&date={date}&base=EUR"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # print(data)
        euro_to_cny_rate = data['rates']['CNY']
        exchange_rates = {'欧元': 1.0, 'CNY': euro_to_cny_rate}
        for currency, rate in data['rates'].items():
            if currency != 'CNY':
                exchange_rates[currency] =  euro_to_cny_rate / rate
        return exchange_rates
    else:
        print("Failed to fetch exchange rates.")
        return None

def save_exchange_rate_to_file(date, rate):
    # 读取已存在的汇率数据，如果文件不存在则创建空字典
    rates = {}
    if os.path.exists(RATE_FILE):
        with open(RATE_FILE, 'r') as file:
            rates = json.load(file)
    
    # 更新汇率数据并保存到文件
    rates[date] = rate
    with open(RATE_FILE, 'w') as file:
        json.dump(rates, file, indent=4)




app = Flask(__name__)


@app.route('/icloud/subscriptions', methods=['GET'])
def get_icloud_subscriptions():
    capacity_size = request.args.get('size', '2TB')

    # 支持指定日期，默认为今天
    formatted_date = request.args.get('date', datetime.today().strftime("%Y-%m-%d"))
    icloud_prices = get_icloud_latest_global_prices(capacity_size, formatted_date)
    return jsonify(icloud_prices)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)
    # icloud_prices = get_icloud_latest_global_prices(url,static_fixer_io_api_key)




