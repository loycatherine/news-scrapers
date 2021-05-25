from english_scraper import NewsDownloader
from chinese_scraper import BaiduNewsDownloader
from chinese_scraper import SogouNewsDownloader
from chinese_scraper import GoogleNewsDownloader

import pandas as pd
from dateutil import relativedelta
from datetime import date
start_date = date.today()
six_months_ago = start_date - relativedelta.relativedelta(months=6)

# df = pd.read_excel('vpc_master_220221.xlsx')
# df_chinese = df[(df['Holding Status'] != 'Exit') & (df['Vertex Entity'] == 'Vertex Ventures China')].reset_index(drop = True)
#
# master_df = df[df['Holding Status'] == 'Active'].reset_index(drop=True)
# df_english = master_df[master_df['Vertex Entity'] != 'Vertex Ventures China'].reset_index(drop=True)
def hello_pubsub(event, context):
    articles_english = NewsDownloader(search_query = 'Signzy', start_date = six_months_ago, end_date = start_date)
    articles_english_df = pd.DataFrame(articles_english.download_news())

    print(articles_english_df)



