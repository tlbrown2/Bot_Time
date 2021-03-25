import yfinance as yf
import numpy as np
import scipy as sp
import pandas as pd
#from talib import RSI,BBANDS,MACD
#from yahoo_fin import stock_info as si


def getTickerPriceData(tickers,period='5d',interval='1d'):
    #Getting Ticker Price Data (Open,High,Close,etc)
    ticker_df = yf.download(tickers=tickers,period=period,interval=interval)
    return ticker_df

def calculate_macd(data,short_window=8,long_window=22,verbose=0):
    EMA_short = data.ewm(halflife=short_window).mean()
    EMA_long = data.ewm(halflife=long_window).mean()
    macd = EMA_short - EMA_long
    #data['MACD H'] = macd
    #data['MACD Signal'] = np.where(df['MACD H'] > 0, 1.0, 0.0)
    macd_signal = np.where(macd > 0, 1.0, 0.0)
    if verbose:
        print(f'The short window is {short_window} & the long window is {long_window}!')
    return macd,macd_signal

def EWMA(data, ndays):
    EMA = pd.Series(data['Close'].ewm(span=ndays, min_periods=ndays - 1).mean(),
                    name='EWMA_' + str(ndays))
    data = data.join(EMA)
    return data

def computeRSI(data, time_window):
    diff = data.diff(1).dropna()  # diff in one field(one day)

    # this preservers dimensions off diff values
    up_chg = 0 * diff
    down_chg = 0 * diff

    # up change is equal to the positive difference, otherwise equal to zero
    up_chg[diff > 0] = diff[diff > 0]

    # down change is equal to negative deifference, otherwise equal to zero
    down_chg[diff < 0] = diff[diff < 0]

    # we set com=time_window-1 so we get decay alpha=1/time_window
    up_chg_avg = up_chg.ewm(com=time_window - 1, min_periods=time_window).mean()
    down_chg_avg = down_chg.ewm(com=time_window - 1, min_periods=time_window).mean()

    rs = abs(up_chg_avg / down_chg_avg)
    rsi = 100 - 100 / (1 + rs)
    return rsi

def calculate_BollingerBands(data,long_window=21):
    ma_long = data.rolling(window=long_window).mean()
    long_std = data.rolling(window=long_window).std()

    upper = ma_long + (long_std * 2)
    lower = ma_long - (long_std * 2)

    return upper,lower

def makeTickerDfSignals(ticker_data_df,interval='1d',short_window=9,long_window=21):
    #Add computational signals to the ticker dataframe

    # Day Length Trade Intervals:

    signals_df = ticker_data_df.loc[:,['Close']].copy()


    # Calculate Daily Returns
    signals_df['Daily_Return'] = signals_df['Close'].dropna().pct_change()
    signals_df.dropna(inplace=True)

    # Generate the short and long moving averages (short window and long window days, respectively)
    signals_df['SMA%s'%short_window] = signals_df['Close'].rolling(window=short_window).mean()
    signals_df['SMA%s'%long_window] = signals_df['Close'].rolling(window=long_window).mean()

    # Initialize the new `Signal` column
    signals_df['Signal'] = 0.0

    signals_df.dropna(inplace=True)
    # Generate the trading signal (1 or 0) to when the short window is less than the long
    # Note: Use 1 when the SMA50 is less than SMA100 and 0 for when it is not.
    signals_df['Signal'][short_window:] = np.where(
        signals_df["SMA%s" % short_window][short_window:] > signals_df["SMA%s" % long_window][short_window:], 1.0,
        0.0)

    # Construct a `Fast` and `Slow` Exponential Moving Average from short and long window close prices, respectively
    signals_df['fast_close_%s'%short_window] = signals_df['Close'].ewm(halflife=short_window).mean()
    signals_df['slow_close_%s'%long_window] = signals_df['Close'].ewm(halflife=long_window).mean()

    # Construct a `Fast` and `Slow` Exponential Moving Average from short and long windows, respectively
    signals_df['fast_vol'] = signals_df['Daily_Return'].ewm(halflife=short_window).std()
    signals_df['slow_vol'] = signals_df['Daily_Return'].ewm(halflife=long_window).std()


    # Calculate the points in time at which a position should be taken, 1 or -1
    signals_df["Entry/Exit"] = signals_df["Signal"].diff()

    # RSI Indicator
    signals_df['RSI'] = computeRSI(signals_df['Close'], time_window=14)

    # MACD Indicator
    macd, macdsignal = calculate_macd(signals_df['Close'],short_window=short_window,long_window=long_window)
    signals_df['MACD'] = macd
    signals_df['MACD_Sig'] = macdsignal

    upper_band,lower_band = calculate_BollingerBands(signals_df['Close'], long_window=long_window)
    signals_df['Upper_Band'] = upper_band
    signals_df['Lower_Band'] = lower_band


    return signals_df