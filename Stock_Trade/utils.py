#moduleをインポート
import datetime
import glob
import numpy as np
import os
import pandas as pd
import re
import requests
from requests_html import HTMLSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome import service as fs
import shutil
import subprocess
import time
from bs4 import BeautifulSoup


"""
初期実行
"""
def InitProcess():
    # ダウンロードデータの保存先
    dt_now = datetime.datetime.now()
    date = dt_now.strftime('%y%m%d')
    downloadDir = os.getcwd() + f"/Stock_Trade/StockData" + date
    try:
        p = glob.glob(os.getcwd() + f"/Stock_Trade/StockData*", recursive=True)[0]
        shutil.rmtree(p)
        logger.info(f"remove {p}")
    except:
        pass
    os.mkdir(downloadDir)


"""
finvizから銘柄の配列を取得
"""
def PickFinviz():
    # URL
    # url = "https://finviz.com/screener.ashx?v=152&f=cap_smallover,exch_nasd&o=-marketcap&c=0,1,2,3,4,6,7,8,26,68,67,65&r="
    url = "https://finviz.com/screener.ashx?v=152&f=cap_smallover,geo_usa&o=-marketcap&c=0,1,2,3,4,6,7,8,26,68,67,65&r="
    # ページ数(num*20銘柄)
    # num = 1
    num = 50
    # ファイル名
    out_path = os.path.join(glob.glob(os.getcwd()+"/Stock_Trade/StockData*", recursive=True)[0], "input.txt")

    with open(out_path, "w", encoding="utf-8") as file:
        # 1ページごとでループする
        for i in range(num):
            page = str(i * 20 + 1)
            site = requests.get(url + page, headers={'User-Agent': 'Custom'})
            data = BeautifulSoup(site.text, 'html.parser')

            tr_tag = data.find_all("tr", {"class": "styled-row is-hoverable is-bordered is-rounded is-striped has-color-text"})
            # 1銘柄ごとループする
            for j in range(0, len(tr_tag), 1):
                a_tag = [a.text for a in tr_tag[j].find_all("a")]
                # 行をテキストファイルに書き込む (波線で区切る)
                file.write("~".join(a_tag[1:]) + "\n")
            print(f"Done {(i+1) * 20}", end="\r")

        print(f"---Done Write input.txt (PickFinviz)---")


"""
ヒストリカルデータをダウンロードする
"""
def HistData():
    # ChromeDriverの保存先
    chromedriver = os.getcwd() + r"/driver/chromedriver"
    # ヒストリカルデータの保存先
    dt_now = datetime.datetime.now()
    date = dt_now.strftime('%y%m%d')
    downloadDir = os.getcwd() + f"/Stock_Trade/StockData" + date
    # 銘柄データの保存先
    stocksDir = glob.glob(os.getcwd() + f"/Stock_Trade/StockData*/input.txt", recursive=True)[0]

    # 銘柄の箱
    symbol = np.full((5000), 0, dtype=object)

    # データ期間の指定（st:開始、ed:終了）
    st = datetime.date(1970, 1, 1)
    ed = datetime.date.today()
    dt = datetime.date(1970, 1, 1)
    st = st - dt
    ed = ed - dt
    st = (st.days) * 86400
    ed = (ed.days) * 86400

    # inputファイルから銘柄群のシンボルを取得
    i = 0
    if(os.path.exists(stocksDir)):
        with open(stocksDir, 'r', encoding='shift-jis') as f:
            for line in f.readlines():
                i += 1
                toks = line.split('~')
                symbol[i] = toks[0]
    # 銘柄数を記録
    nsym = i

    #ドライバの設定
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--headless')
    options.add_experimental_option("prefs", {"download.default_directory": downloadDir })

    # chrome_service = fs.Service(executable_path=chromedriver)
    # driver = webdriver.Chrome(service=chrome_service, chrome_options=options)
    driver = webdriver.Chrome(chromedriver, chrome_options=options)

    # headlessモードでファイルをダウンロードする際の追加設定
    driver.command_executor._commands["send_command"] = (
    'POST',
    '/session/$sessionId/chromium/send_command'
    )
    driver.execute(
        'send_command',
        params={
            'cmd': 'Page.setDownloadBehavior',
            'params': {'behavior': 'allow', 'downloadPath': downloadDir}
        }
    )


    # IXICのヒストリカルデータをダウンロード
    url = 'https://query1.finance.yahoo.com/v7/finance/download/^IXIC?period1='\
            +str(st)+'&period2='+str(ed)+'&interval=1d&events=history&includeAdjustedClose=true'

    #日足データのダウンロード
    driver.implicitly_wait(30)
    driver.get(url)
    #2秒間の一時停止
    time.sleep(2)

    #銘柄数の分だけループ
    for i in range(1,nsym+1):
        url = 'https://query1.finance.yahoo.com/v7/finance/download/'+str(symbol[i])+'?period1='\
                +str(st)+'&period2='+str(ed)+'&interval=1d&events=history&includeAdjustedClose=true'
        #日足データのダウンロード
        driver.implicitly_wait(30)
        driver.get(url)

        print(f"{str(symbol[i])} {int(i)}/{int(nsym)} ", end="\r")

        #2秒間の一時停止
        time.sleep(2)

    print(f"---Done Download HistData (HistData)---")



"""
IXICのヒストリカルデータの列を増やす
"""
def ProcessNASDAQ():
    # IXICのCSVを読み込む
    IXICdir = glob.glob(os.getcwd() + f"/Stock_Trade/StockData*/^IXIC.csv", recursive=True)[0]
    df = pd.read_csv(IXICdir)

    # 追加する列
    # 50日移動平均線
    df['SMA50'] = df['Adj Close'].rolling(50).mean()
    # 150日移動平均線
    df['SMA150'] = df['Adj Close'].rolling(150).mean()
    # 200日移動平均線
    df['SMA200'] = df['Adj Close'].rolling(200).mean()
    # 200日移動平均線の20日平均値
    df['SMA200 mean 20days'] = df['SMA200'].rolling(20).mean()
    # 200日移動平均線の20日前の値
    df['SMA200 befor 20days'] = df['SMA200'].shift(20)
    # 200日移動平均線と現在の株価のギャップ
    df['SMA200 Gap'] = df['Adj Close'] / df['SMA200']
    # 52週最高値
    df['52W High'] = df['Adj Close'].rolling(260, min_periods=1).max() # min_periodsを使用して1つ以上のデータがあった場合の最大値を求める
    # 52週最高値の25%以内
    df['52W High*0.75'] = df['52W High']*0.75
    # 52週最安値
    df['52W Low'] = df['Adj Close'].rolling(260, min_periods=1).min() # min_periodsを使用して1つ以上のデータがあった場合の最小値を求める
    # 52週最安値の30%以上
    df['52W Low*1.3'] = df['52W Low']*1.3
    # UpDownVolumeRatio
    # 前日と比較し株価が上昇していた日の出来高を'Up'に、下落していた日の出来高を'Down'に格納する
    df['Up'] = df.loc[df['Adj Close'].diff() > 0, 'Volume']
    df['Down'] = df.loc[df['Adj Close'].diff() <= 0, 'Volume']
    # 欠損値を0で埋める
    df = df.fillna(0)
    # 過去50営業日のうち株価が上昇した日の出来高を下落した日の出来高で割った数値
    df['U/D'] = df['Up'].rolling(50).sum() / df['Down'].rolling(50).sum()

    # ミネルビィ二のトレンドテンプレートのNo1〜No7までの列を作成
    df[['No1', 'No2', 'No3', 'No4', 'No5', 'No6', 'No7']] = 0

    # No1 現在の株価が150日と200日の移動平均線を上回っている。
    df.loc[(df['Adj Close'] > df['SMA150']) & (df['Adj Close'] > df['SMA200']), 'No1'] = int(1)
    # No2 150日移動平均線は200日移動平均線を上回っている。
    df.loc[df['SMA150'] > df['SMA200'], 'No2'] = int(1)
    # No3 200日移動平均線は少なくとも1か月、上昇トレンドにある。
    df.loc[df['SMA200 mean 20days'] > df['SMA200 befor 20days'], 'No3'] = int(1)
    # No4 50日移動平均線は150日移動平均線と200日移動平均線を上回っている。
    df.loc[(df['SMA50'] > df['SMA150']) & (df['SMA50'] > df['SMA200']), 'No4'] = int(1)
    # No5 現在の株価は50日移動平均線を上回っている。
    df.loc[df['Adj Close'] > df['SMA50'], 'No5'] = int(1)
    # No6 現在の株価は52週安値よりも、少なくとも30％高い。
    df.loc[df['Adj Close'] > df['52W Low*1.3'], 'No6'] = int(1)
    # No7 現在の株価は52週高値から少なくとも25％以内にある。
    df.loc[df['Adj Close'] > df['52W High*0.75'], 'No7'] = int(1)
    # No1~No7の合計値
    df['Total'] = df['No1'] + df['No2'] + df['No3'] + df['No4'] + df['No5'] + df['No6'] + df['No7']

    # 買い条件1
    df['BuyFlg1'] = 0
    # 買い条件2
    df['BuyFlg2'] = 0
    df.loc[df['U/D'] >= 1, 'BuyFlg2'] = int(1)
    # 買い条件3
    df['BuyFlg3'] = 0
    df.loc[(df['Total'] >= 5) & (df['No1'] == 1) & (df['No4'] == 1) & (df['No5'] == 1) & (df['No6'] == 1), 'BuyFlg3'] = int(1)
    # 売り条件1
    df['SellFlg1'] = 0
    df.loc[df['Total'] <= 4, 'SellFlg1'] = int(1)
    # 売り条件2
    df['SellFlg2'] = 0
    df.loc[df['Adj Close'] < df['SMA200'], 'SellFlg2'] = int(1)

    # Totalの列を^IXIC Totalに変更する
    df.rename(columns={'Total': '^IXIC Total'}, inplace=True)
    # Csvの書き出し
    df.to_csv(IXICdir, index=False)

    print(f"---Done Process ProcessNASDAQ (ProcessNASDAQ)---")


"""
個別株のヒストリカルデータの列を増やす
"""
def ProcessHistData():
    # IXICのCSVを読み込む
    IXICdir = glob.glob(os.getcwd() + f"/Stock_Trade/StockData*/^IXIC.csv", recursive=True)[0]
    dfIXIC = pd.read_csv(IXICdir)

    # 各企業のヒストリカルデータを読み込む
    cnt=0
    files = glob.glob(os.getcwd() + "/Stock_Trade/StockData*/*.csv", recursive=True)
    files.remove(IXICdir) # IXICのファイルを除く
    # Comprehensiveのファイルを除く
    compdir = glob.glob(os.getcwd() + f"/Stock_Trade/StockData*/Comprehensive.csv", recursive=True)[0]
    files.remove(compdir)
    mnum=len(files)
    for file in files:
        # 入力CSV
        df = pd.read_csv(file)
        s = re.sub(os.getcwd() + r"/Stock_Trade/StockData[0-9]{6}/|.csv", "", file)

        # 'IXIC Total'列が複数結合されるのを防ぐため(本実装時には何度も当ファイルを実行されることが無いため当コードは不要と思う)
        if not '^IXIC Total' in df.columns:
            # 入力CSVと^IXICのCSVを結合する
            df = pd.merge(df, dfIXIC[['Date', '^IXIC Total']], on='Date', how='inner')

        # 追加する列
        # 10日移動平均線
        df['SMA10'] = df['Adj Close'].rolling(10).mean()
        # 21日指数平滑移動平均線
        df['EMA21'] = df['Adj Close'].ewm(21).mean()
        # 50日移動平均線
        df['SMA50'] = df['Adj Close'].rolling(50).mean()
        # 150日移動平均線
        df['SMA150'] = df['Adj Close'].rolling(150).mean()
        # 200日移動平均線
        df['SMA200'] = df['Adj Close'].rolling(200).mean()
        # 200日移動平均線の20日平均値
        df['SMA200 mean 20days'] = df['SMA200'].rolling(20).mean()
        # 200日移動平均線の20日前の値
        df['SMA200 befor 20days'] = df['SMA200'].shift(20)
        # 200日移動平均線と現在の株価のギャップ
        df['SMA200 Gap'] = df['Adj Close'] / df['SMA200']
        # 出来高の50日移動平均線
        df['Volume SMA50'] = df['Volume'].rolling(50).mean()
        # 52週最高値
        df['52W High'] = df['Adj Close'].rolling(260, min_periods=1).max() # min_periodsを使用して1つ以上のデータがあった場合の最大値を求める
        # 52週最高値の25%以内
        df['52W High*0.75'] = df['52W High']*0.75
        # 52週最安値
        df['52W Low'] = df['Adj Close'].rolling(260, min_periods=1).min() # min_periodsを使用して1つ以上のデータがあった場合の最小値を求める
        # 52週最安値の30%以上
        df['52W Low*1.3'] = df['52W Low']*1.3
        # UpDownVolumeRatio 過去50営業日のうち株価が上昇した日の出来高を下落した日の出来高で割った数値
        df['Up'] = df.loc[df['Adj Close'].diff() > 0, 'Volume'] # 前日と比較し株価が上昇していた日の出来高を'Up'
        df['Down'] = df.loc[df['Adj Close'].diff() <= 0, 'Volume'] # 前日と比較し株価が下落していた日の出来高を'Down'に格納する
        df = df.fillna(0) # 欠損値を0で埋める
        df['U/D'] = df['Up'].rolling(50).sum() / df['Down'].rolling(50).sum()
        # ATH
        df['ATH'] = df['Adj Close'].max()

        # ミネルビィ二のトレンドテンプレートのNo1〜No7までの列を作成
        df[['No1', 'No2', 'No3', 'No4', 'No5', 'No6', 'No7']] = 0

        # No1 現在の株価が150日と200日の移動平均線を上回っている。
        df.loc[(df['Adj Close'] > df['SMA150']) & (df['Adj Close'] > df['SMA200']), 'No1'] = int(1)
        # No2 150日移動平均線は200日移動平均線を上回っている。
        df.loc[df['SMA150'] > df['SMA200'], 'No2'] = int(1)
        # No3 200日移動平均線は少なくとも1か月、上昇トレンドにある。
        df.loc[df['SMA200 mean 20days'] > df['SMA200 befor 20days'], 'No3'] = int(1)
        # No4 50日移動平均線は150日移動平均線と200日移動平均線を上回っている。
        df.loc[(df['SMA50'] > df['SMA150']) & (df['SMA50'] > df['SMA200']), 'No4'] = int(1)
        # No5 現在の株価は50日移動平均線を上回っている。
        df.loc[df['Adj Close'] > df['SMA50'], 'No5'] = int(1)
        # No6 現在の株価は52週安値よりも、少なくとも30％高い。
        df.loc[df['Adj Close'] > df['52W Low*1.3'], 'No6'] = int(1)
        # No7 現在の株価は52週高値から少なくとも25％以内にある。
        df.loc[df['Adj Close'] > df['52W High*0.75'], 'No7'] = int(1)
        # No1~No7の合計値
        df['Total'] = df['No1'] + df['No2'] + df['No3'] + df['No4'] + df['No5'] + df['No6'] + df['No7']

        # 買い条件1
        df['BuyFlg1'] = 0
        df.loc[dfIXIC['^IXIC Total'] >=2, 'BuyFlg1'] = int(1)
        # 買い条件2
        df['BuyFlg2'] = 0
        df.loc[df['U/D'] >= 1, 'BuyFlg2'] = int(1)
        # 買い条件3
        df['BuyFlg3'] = 0
        df.loc[(df['Total'] >= 5) & (df['No1'] == 1) & (df['No4'] == 1) & (df['No5'] == 1) & (df['No6'] == 1), 'BuyFlg3'] = int(1)
        # 売り条件1
        df['SellFlg1'] = 0
        df.loc[df['Total'] <= 4, 'SellFlg1'] = int(1)
        # 売り条件2
        df['SellFlg2'] = 0
        df.loc[df['Adj Close'] < df['SMA200'], 'SellFlg2'] = int(1)
        # # 買い控え条件1
        # df['NotBuyFlg1'] = 0
        # df.loc[(df['Total'] == 5) & (df['No7'] == 1), 'NotBuyFlg1'] = int(1)

        # 8%で売る
        # df.loc[df['BuyPrice']/ df['Adj Close'] >= 1.08, 'SellFlg3'] = int(1)

        try:
            # 買っているフラッグ
            df['BuyingFlg'] = 0
            # df.loc[(df['BuyFlg1'] == 1) & (df['BuyFlg2'] == 1) & (df['BuyFlg3'] == 1) & (df['NotBuyFlg1'] != 0) , 'BuyingFlg'] = int(1)
            df.loc[(df['BuyFlg1'] == 1) & (df['BuyFlg2'] == 1) & (df['BuyFlg3'] == 1) , 'BuyingFlg'] = int(1)
            df.loc[df['BuyingFlg'].shift(1) == 1, 'BuyingFlg'] = int(0)
            # 売ったフラッグ
            df['SelledFlg'] = 0
            df.loc[(df['BuyingFlg'].cumsum() >= 1) & (df['SellFlg1'] == 1) | (df['SellFlg2'] == 1), 'SelledFlg'] = int(1) # 該当行より上の行でBuyingFlgが立っていれば立てる
            df.loc[df['SelledFlg'].shift(1) == 1, 'SelledFlg'] = int(0)

            # 'BuyingFlg'または'SelledFlg'が1のものを選出する
            df_trade = df[(df['BuyingFlg'] == 1) | (df['SelledFlg'] == 1)]
            # 'BuyingFlg'と'SelledFlg'各々の1が続く行をすべて0に変換する
            df_trade.loc[df_trade['BuyingFlg'].shift(1) == 1, 'BuyingFlg'] = int(0)
            df_trade.loc[df_trade['SelledFlg'].shift(1) == 1, 'SelledFlg'] = int(0)
            # 'BuyingFlg'または'SelledFlg'の値が1であるもののみを選出する
            df_trade = df_trade[(df_trade['BuyingFlg'] == 1) | (df_trade['SelledFlg'] == 1)]

            # # 買い値
            # df_trade['BuyPrice'] = 0
            # df_trade.loc[df_trade['BuyingFlg'] == 1, 'BuyPrice'] = df_trade['Adj Close']

            # dfの一番初めがSelledFlgで始まった場合はその行を消す
            if df_trade['SelledFlg'].iloc[0] == 1:
                df_trade = df_trade.iloc[1:]


            # 利益率
            df_trade['Earn'] = 0
            # df_trade.loc[df_trade['SelledFlg'] == 1, 'Earn'] = (df_trade['Adj Close'] / df_trade['Adj Close'].shift(1) - 1) * 100
            df_trade.loc[df_trade['SelledFlg'] == 1, 'Earn'] = df_trade['Adj Close'] / df_trade['Adj Close'].shift(1)

            # 元のBuyingFlgとSelledFlgをすべて0にする
            df[['BuyingFlg', 'SelledFlg']] = 0

            # 利益率をdfに追加するために結合
            #'Earn'列が複数結合されるのを防ぐため(本実装時には何度も当ファイルを実行されることが無いため当コードは不要と思う)
            if not 'Earn' in df.columns:
                # 入力CSVとdf_tradeのCSVを結合する
                df = pd.merge(df, df_trade[['Date', 'Earn']], on='Date', how='outer').fillna(0)

            # dfにBuyingFlgとSelledFlgの値を結合する
            df = pd.merge(df, df_trade[['Date', 'BuyingFlg', 'SelledFlg']], on='Date', how='outer')
            # 重複した列を削除し、列名を変更する
            df = df.drop(['BuyingFlg_x', 'SelledFlg_x'], axis=1).rename(columns={'BuyingFlg_y': 'BuyingFlg', 'SelledFlg_y': 'SelledFlg'})

            # 総利益率
            # df['TotalEarn'] = df[df['Earn'] != 0]['Earn'].cumsum()
            df['TotalEarn'] = np.cumprod(df[df['Earn'] != 0]['Earn'])
            # 0の箇所を前の値で埋める
            df['TotalEarn'] = df['TotalEarn'].fillna(method='pad')
            df = df.fillna(0)

            # 買い値
            df.loc[df['BuyingFlg'] == 1, 'BuyPrice'] = df['Adj Close']
            # 0の箇所を前の値で埋める
            df = df.fillna(method='pad')

            # 空白を0で埋める
            df = df.fillna(0)

        # 取引履歴がない場合Empty DataFrameエラーが発生するのでその場合は2つの列を追加する
        except:
            df[['Earn', 'TotalEarn']] = float(0)

        df.to_csv(file, index=False)
        cnt+=1
        print(f"{s} {cnt}/{mnum} ",end="\r")

    print(f"---Done Process ProcessHistData (ProcessHistData)---")