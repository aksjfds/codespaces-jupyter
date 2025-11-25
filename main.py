from okx import PublicData
import okx.MarketData as MarketData
import pandas as pd
import warnings
import time

pd.set_option('display.max_rows', None)
warnings.filterwarnings('ignore')

# 获取币种
public = PublicData.PublicAPI(flag='0')
data = public.get_instruments('SWAP')['data']
names = [x['instId'] for x in data if  "USDT-SWAP" in x['instId']]

# 获取k线
market = MarketData.MarketAPI(flag='0')
def get_candles(instId='ETH-USDT-SWAP', bar='1H', limit="100"):
    result = market.get_candlesticks(instId=instId, bar=bar, limit=limit)

    data = result['data']  # 列表，每项：[ts, o, h, l, c, vol, volCcy, ...]
    df = pd.DataFrame(data, columns=[
        'ts', 'open', 'high', 'low', 'close', 
        'vol', 'volCcy', 'volCcyQuote', 'confirm'
    ])
    df = df.loc[:, ["open", "high", "low", "close"]]
    df = df.astype({'open':float, 'high':float, 'low':float, 'close':float})
    df = df[::-1].reset_index(drop=True)    # 最后一行为新k

    return df

# supertrend 算法
def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=10, atr_multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
        
    return df

# 主要逻辑
def main():
    for name in names:
        candles_15m = get_candles(name, bar='15m')
        supertrend_15m = supertrend(candles_15m)
        supertrend_15m = supertrend_15m["in_uptrend"]    
        current_trend_15m = supertrend_15m.iloc[-1]

        # 不为下跌趋势就跳过
        if current_trend_15m != False:
            continue

        candles_1H = get_candles(name, bar='1H')
        supertrend_1H = supertrend(candles_1H)
        supertrend_1H = supertrend_1H["in_uptrend"]
        current_trend_1H = supertrend_1H.iloc[-1]
        prev_trend_1H = supertrend_1H.iloc[-2]


        # 上升趋势转为下跌趋势
        if current_trend_1H == False and prev_trend_1H == True:
            print(name)



while True:
    main()
    time.sleep(3600)