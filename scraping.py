import requests, json, csv
import click
from bs4 import BeautifulSoup
import os

ACCESS_TOKEN = ''
JSESSIONID = ''
LAST_SOUP = {}
DEFAULT_DATA = ['', '', '', '', '', '', '', '', '', '']  # Data 8 col
# DEFAULT_DATA = ['']  # Data 8 col

def lineNoti(msg):
    urlLine = 'https://notify-api.line.me/api/notify'
    token = 'nVCDZg1I4UiztlhcZe2C14MhUCijNUX4421KcjUmBeZ'
    headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer ' + token}

    requests.post(urlLine, headers=headers , data = {'message': msg})

def readCodes(name='code.csv'):
    codes = []
    with open('./raw_data/' + name, mode='r', encoding='utf-8-sig') as code_file:
        csv_reader = csv.reader(code_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            codes.append([str(row[0])])
            line_count += 1
    code_file.close()

    return codes

def checkCookie(jsid):
    query_headers = {
        'Cookie': "JSESSIONID=" + jsid + ";"
    }
    querystring = { "locale": "en_US", "symbol": "ADVA01C1905A" }
    url = 'https://www.setsmart.com/ism/companyprofile.html'
    r = requests.get(url, headers=query_headers, params=querystring)

    return True if str(r.content).find("Sorry, You don't have permission") < 0 else False

def login(user = '', pwd = ''):

    global JSESSIONID

    username = os.environ['SETSMART_USERNAME']
    password = os.environ['SETSMART_PASSWORD']
    print(username)
    print(password)
    payload = "{\n    \"password\": \"%s\",\n    \"username\": \"%s\"\n}" %(password, username)
    print(payload)

    headers = {
        'Content-Type': "application/json",
        'User-Agent': "PostmanRuntime/7.15.2",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "9b2fa27c-4052-477a-94f0-9f2482765e41,392e6b9e-f3ad-49db-bf29-2b4e03cfb78d",
        'Host': "api.setsmart.com",
        'Accept-Encoding': "gzip, deflate",
        'Content-Length': "66",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    with requests.Session() as s:
        url = 'https://api.setsmart.com/api/user/login'
        r = s.post(url, data=payload, headers=headers)
        
        ACCESS_TOKEN = r.json()['access_token']
        r_create_session = s.get('https://www.setsmart.com/ism/api/createusersession.api', headers={'Authorization': 'Bearer ' + ACCESS_TOKEN})
        
        JSESSIONID = s.cookies.get_dict()['JSESSIONID']
        return {'session': s}

def get_html(url, headers={}, params={}):
    try:
        # Get Page
        r = requests.get(url, headers=headers, params=params)
        return r.content
        
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        lineNoti(' : network error when scraping : ' + url + ' | ' + str(e))
        get_html(url, headers, params)
        return False
        # sys.exit(1)

def get_iframe_URL(code):

    global JSESSIONID
    global LAST_SOUP

    query_headers = { 'Cookie': "JSESSIONID=" + JSESSIONID + ";" }
    query_string = { "locale": "en_US", "symbol": code }

    html_doc = get_html('https://www.setsmart.com/ism/companyprofile.html', query_headers, query_string)
    if str(html_doc).find('No Symbol Found') >= 0:
        print('No Symbol Found')
        return None
    if html_doc == False: 
        return False

    soup = BeautifulSoup(html_doc, 'html.parser')
    LAST_SOUP = soup

    if soup.iframe == None:
        login()
        html_doc = get_html('https://www.setsmart.com/ism/companyprofile.html', query_headers, query_string)
        soup = BeautifulSoup(html_doc, 'html.parser')

        if soup.iframe == None:
            return False

    if len(soup.find_all('iframe')) <= 1:
        return False

    return soup.find_all('iframe')[1].get('src') # first iFrame is GA (Google Analytic)

@click.command()
@click.option('--cookie', default='2F2BF38D029E43EC58C3AEFBDE512635.localhost')
@click.option('--start', default=0)
@click.option('--end', default=1)
@click.option('--file', default='code.csv')
def process(cookie, start, end, file) :
    
    global JSESSIONID
    global LAST_SOUP

    login_info = login()
    print(login_info)
    
    query_headers = {
        'Cookie': "JSESSIONID=" + JSESSIONID + ";"
    }

    lineNoti('Start Scraping s:' + str(start) + ' e: ' + str(end) + ' | Cookie ' + "JSESSIONID=" + JSESSIONID + ";")

    codes = readCodes(file)

    start_row = start
    end_row = end
    all_row = end - start
    count_row = 0
    count_loop = 0

    if checkCookie(JSESSIONID) == True:

        with open('./process_data/data-' + str(start_row+1) + '-' + str(end_row) + '.csv', 'w+') as csv_file, open('./raw_data/code-run-again.csv', 'a+') as csv_file_again:

            writer = csv.writer(csv_file)
            writer_again = csv.writer(csv_file_again)

            for code in codes[start_row:end_row]:

                count_loop += 1
                
                com_code = code[0]
                
                print(f'{count_loop} : Prepare com code {com_code}')
                
                data_url = get_iframe_URL(com_code)
                if data_url == None:
                    code = code + DEFAULT_DATA
                    writer.writerow(code)
                    continue
                if data_url == False:
                    code = code + DEFAULT_DATA
                    writer_again.writerow([com_code])

                # above data (dont iFrame)
                above_data = []
                above_data_find_list = [
                    'No. of Listed Share',
                    'Exercise Price',
                    'Market Maker',
                    'Issuer/Guarantor Credit Rating',
                    'Credit Rating Agency',
                    '% of the Outstanding Units to the Total Units of Listed Derivative Warrants'
                ]
                for find_str in above_data_find_list:
                    # Find data_no_issued_shares
                    dnis = LAST_SOUP.find('td', text=find_str)
                    if (dnis == None):
                        above_data += [None]
                        # data_no_issued_shares = None
                    else:
                        above_data += [dnis.find_next_sibling('td').string]
                        # data_no_issued_shares = dnis.find_next_sibling('td').string

                
                # start get data from iFrame
                if data_url != False:
                    try:
                        #Get Data
                        str_data = ""
                        url = 'https://www.setsmart.com' + str(data_url)
                        soup = BeautifulSoup(get_html(url, query_headers), 'html.parser')
                        LAST_SOUP = soup

                        if soup.pre == None:
                            lineNoti(f'{com_code} soup again')
                            soup = BeautifulSoup(get_html(url, query_headers), 'html.parser')
        
                            if soup.pre == None:
                                code = code + DEFAULT_DATA
                            else:
                                str_data = soup.pre.string.replace(" ", "").lower()
                        else:
                            str_data = soup.pre.string.replace(" ", "").lower()
                        
                    except requests.exceptions.RequestException as e:  # This is the correct syntax
                        lineNoti(com_code + ' : network error when scraping : ' + url)
                        writer_again.writerow(com_code)
                        continue
                        #sys.exit(1)

                    # Scraping Data
                    # print(str_data)
                    
                    # find data
                    col_name = [
                        # 'dwvalue(baht):', #0
                        # 'exerciseratio(dw:underlyingasset):', #1
                        # 'exerciseratio(calculate):', #2
                        # 'exerciseprice(baht):', #3
                        # 'tradingdate:', #4
                        # 'lasttradingdate:', #5
                        # 'maturitydate:', #6
                        # 'lastexercisedate:', #7
                        'underlyingasset:',
                        'issueprice(baht/unit):',
                        'distributedate:',
                        'exerciseratio(dw:underlyingasset):'
                    ]
                    
                    if str_data != "":
                        get_data = {}
                        for name in col_name:
                            index_start = str_data.find(name, 0)
                            index_end = str_data.find('\n', index_start)
                            
                            if index_start == -1:
                                if name == 'dwvalue(baht):':
                                    index_start = str_data.find('dwvalue(bath):', 0)
                                    index_end = str_data.find('\n', index_start)
                                    if index_start == -1:
                                        get_data[name] = ""
                                        continue
                                else:
                                    get_data[name] = ""
                                    continue
                                    
                            data = str_data[index_start + len(name):index_end]
                            get_data[name] = data.replace('\r', '')
                        
                        code = code + list(map(lambda name: get_data[name], col_name))

                for adata in above_data:
                    if adata == None:
                        code = code + ['']
                    else:
                        code = code + [adata.replace('\n', '').replace('\r', '').replace('\xa0', '').replace(' ', '').replace('Shares', '')]
                
                writer.writerow(code)

                print(f'Data com code {code}')
                
                count_row += 1

        csv_file.close()
        csv_file_again.close()
        lineNoti('Web Scraping (s:' + str(start) + ' e: ' + str(end) + ') Done :)')

    else:
        click.echo('Please find any session again')

    click.echo('finish row count = %d, all row = %d' % (count_row, all_row))

if __name__ == '__main__':
    process()