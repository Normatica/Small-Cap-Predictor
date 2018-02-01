import pandas as pd
import numpy as np
import datetime
from math import isnan
import pathlib
from src.define_target import DefineTarget
from src.general_functions import GeneralFunctions
from emails.send_emails import Email


class CombineData(Email,GeneralFunctions):

    def __init__(self):
        super().__init__()
        self.message_board_posts = self.load_file('message_board_posts')
        self.stock_prices = self.load_file('stock_prices')
        self.ticker_symbols = self.load_file('ticker_symbols')

    def _calculate_ohlc(self,df):
        '''
        OHLC Average (open-high-low-close) is a commonly used indicator to
        determine a stock price on a given day
        Dollar Volume is a better predictor than volume alone. i.e. a stock trading
        1M volume at a $0.10 price should be treated differently than a stock
        trading 1M volume at a $10 price

        Parameters
        ----------
        df: pandas dataframe, stock price info

        Output
        ------
        df: pandas dataframe, ohlc and dollar volume of stock
        '''

        #fillna's
        df.fillna(0.00,inplace = True)

        #create ohlc column
        df.loc[:,'ohlc'] = df.loc[:,['Open','High','Low','Close']].mean(axis=1)

        #create dollar volumne column
        df.loc[:,'dollar_volume'] = (df.ohlc * df.Volume)
        df = df.drop(['Open','Close','High','Low','Volume'],axis=1)
        df.index = pd.to_datetime(df.index)
        return df

    def _remove_weekends_and_holidays(self, df):
        '''
        The stock market is not open on weekends and federal holidays. These
            days will not be included
        '''
        weekend_dates = set(df[df.weekday > 4].index)
        holiday_dates = set(pd.to_datetime(self.load_file('stock_market_holidays').date))
        # holiday_dates = set(pd.to_datetime(pd.read_csv('data/tables/stock_market_holidays.csv').date))
        return df.drop(holiday_dates.union(weekend_dates),errors='ignore')

    def compile_data(self):
        '''
        Combines data from ihub message boards, and stock price history
            databases and calculates the target.
        '''

        first = True
        for _, stock in self.ticker_symbols.iterrows():
            try:
                symbol = stock['symbol']
                print ('Compiling data for ' + symbol)
                mbp = self.message_board_posts[self.message_board_posts.symbol == symbol]
                mbp.index = pd.to_datetime(mbp.date)
                grouped_posts = mbp.post_number

                sp = self.stock_prices[self.stock_prices.symbol == symbol]
                # mbp = mbp.drop('symbol',axis=1)
                sp = sp.drop('symbol',axis=1)
                sp = self._calculate_ohlc(sp)

                # grouped_posts = mbp.groupby('date').count().post_number
                # grouped_posts.index = pd.to_datetime(grouped_posts.index)

                start_date = max([min(grouped_posts.index.tolist()),min(sp.index.tolist())])
                end_date = max([max(grouped_posts.index.tolist()),max(sp.index.tolist())])
                df_date = pd.DataFrame(pd.date_range(start_date,end_date)).set_index(0)

                combined_data = df_date.join(grouped_posts).join(sp)
                combined_data['weekday'] = combined_data.index.weekday
                combined_data = self._remove_weekends_and_holidays(combined_data)
                combined_data.index.name = 'date'
                combined_data.fillna(0,inplace=True)

                t = DefineTarget(combined_data)
                combined_data['target'] = t.target

                combined_data['symbol'] = symbol

                if first == True:
                    final = combined_data
                    first = False
                else:
                    final = pd.concat([final,combined_data])
            except:
                self.send_email('error','Problem with {0}'.format(symbol))
                print ('Error for {0}'.format(symbol))

        self.save_file(final,'combined_data')

if __name__ == '__main__':

    CombineData().compile_data()
