#!/usr/bin/env python
# coding: utf-8

# In[24]:


import pandas as pd
import numpy as np
import re
import string
import seaborn as sns
from matplotlib import pyplot as plt

import hanzidentifier
from google_trans_new import google_translator
import textwrap

from GoogleNews import GoogleNews
from newspaper import Article
import requests
import nltk
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from time import strftime
from time import sleep
import datetime
from datetime import date
from dateutil import relativedelta

from __future__ import print_function
import json


# ## Load Company Data

# In[4]:


df = pd.read_excel('vpc_master_220221.xlsx')


# In[5]:


df = df[(df['Holding Status'] != 'Exit') & (df['Vertex Entity'] == 'Vertex Ventures China')].reset_index(drop = True)


# In[6]:


df.head(5)


# In[ ]:





# ### Preparation

# In[7]:


# Date preparation - 2 years ago, 1 year ago, 6 months ago, 1 month ago
# Reference date: today

# Starting date will be Jan 2021

# start_date = datetime.date(2021, 1, 1)
# one_month_ago = start_date - relativedelta.relativedelta(months=1)
# six_months_ago = start_date - relativedelta.relativedelta(months=6)
# one_year_ago = start_date - relativedelta.relativedelta(months=12)
# two_years_ago = start_date - relativedelta.relativedelta(months=24)


# In[ ]:





# ### Split on Optimized Search Engine

# In[8]:


baidu_df = df[df['Optimized Search Engine'] == 'Baidu'].reset_index(drop=True)
google_df = df[df['Optimized Search Engine'] == 'Google'].reset_index(drop=True)
sogou_df = df[df['Optimized Search Engine'] == 'Sogou'].reset_index(drop=True)


# In[9]:


print("baidu:", len(baidu_df))
print("sogou:", len(sogou_df))
print("google:", len(google_df))


# In[ ]:





# ## Pull Baidu News

# In[27]:


# Input search query (e.g. company name), start_date, end_date
# Output df of search result, one per row

class BaiduNewsDownloader:
    def __init__(self, search_query, start_date, end_date):
        self.search_query = search_query
        self.start_date = start_date
        self.end_date = end_date
        
    def get_news_articles(self):
        options = Options()
        options.add_argument('--headless')
        # create a new Chrome session
        driver = webdriver.Chrome(options=options)
        # if no chrome driver:
        # driver = webdriver.Chrome(ChromeDriverManager().install())
        
        # URL for 1) baidu news 2) sorted by time 3) for the search query
        search_url = 'https://www.baidu.com/s?tn=news&rtt=4&bsst=1&cl=2&wd=' + self.search_query + '&medium=0'
        driver.get(search_url)
        delay = 3 # seconds
        
        try:
            checkElement = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH, "//div[@class='news-source']/span[2]")))
            print("Page is ready. Searching:", self.search_query)
            
        except TimeoutException:
            print("Loading took too much time.")
        
        
        # ----------------- Get dates -----------------
        raw_dates_list = driver.find_elements_by_xpath("//div[@class='news-source']/span[2]") # selenium object
        
        dates_list = []
        for date in raw_dates_list:
            if len(date.text) > 10:
                string_date = re.sub('[^0-9]', ' ', date.text) # format in YYYY-M-D (%Y-%m-%d)
                string_date = string_date.strip()
                string_date = string_date.replace(" ", "-")
                    
                format_date = datetime.datetime.strptime(string_date, '%Y-%m-%d').date() 

                if self.end_date >= format_date >= self.start_date: # filter out for time period specified
                    dates_list.append(format_date)
                    
            else: # for news that just came out and so doesnt have standard datetime format on baidu
                dates_list.append('Less than 24hr ago')
                
        
        # ----------------- Get news source -----------------
        raw_source_list = driver.find_elements_by_xpath("//div[@class='news-source']/span[1]")
        translator = google_translator()
        
        source_list = []
        for source in raw_source_list:
            if hanzidentifier.has_chinese(source.text):
                trans_source = translator.translate(source.text, lang_tgt='en')
                time.sleep(3)
                source_list.append(trans_source)
            else:
                raw_source = source.text
                source_list.append(raw_source)

        
        # ----------------- Get URLs & articles -----------------
        articles_no = len(dates_list)
        if articles_no > 0:
            
            headlines_list = []
            links_list = []
            headlines = driver.find_elements_by_xpath('//h3/a')[:articles_no]
            
            for headline in headlines:
                title = headline.text
                headlines_list.append(title)
                
            for link in headlines:
                url = link.get_attribute('href')
                links_list.append(url)
                
            summaries_list = []
            summaries = driver.find_elements_by_xpath("//span[@class='c-font-normal c-color-text']")[:articles_no]
            for summary in summaries:
                short_text = summary.text
                summaries_list.append(short_text)

            articles_list = []
            for i in range(len(links_list)):
                try:
                    article_dict = {}
                    article = Article(links_list[i], language = 'zh')
                    article.download()
                    article.parse()

                    article_dict['Search Query'] = self.search_query
                    article_dict['Date'] = dates_list[i]
                    article_dict['Source'] = source_list[i]
                    article_dict['URL'] = links_list[i]
                    
                    # translate headlines 
                    translator = google_translator()
                    raw_title = headlines_list[i]
                    article_dict['Title'] = translator.translate(raw_title, lang_tgt='en')
                    time.sleep(3)
                    
                    # use snippets if article.text is empty or article.text is too long for translation
                    if article.text == '' or len(article.text) > 5000:
                        raw_summary = summaries_list[i] 
                        article_dict['Article'] = translator.translate(raw_summary, lang_tgt='en')
                    else:
                        raw_article = re.sub('\n\n', ' ', article.text)
                        article_dict['Article'] = translator.translate(raw_article, lang_tgt='en')
    
                    articles_list.append(article_dict)
                except:
                    continue

            articles_df = pd.DataFrame(articles_list)

        else: 
            articles_df = pd.DataFrame({
                'Search Query': self.search_query,
                'Date': [np.nan],
                'Source': [np.nan],
                'URL': [np.nan],
                'Title': [np.nan],
                'Article': [np.nan]
            })
        
        driver.quit()
            
        return articles_df


# In[112]:


articles = BaiduNewsDownloader(search_query = '伏达半导体', start_date = six_months_ago, end_date = start_date) 


# In[113]:


df = articles.get_news_articles()


# In[99]:


df


# In[ ]:





# ## Pull Sogou News

# In[67]:


class SogouNewsDownloader:
    def __init__(self, search_query, start_date, end_date):
        self.search_query = search_query
        self.start_date = start_date
        self.end_date = end_date
    
    def get_news_articles(self):
        driver = webdriver.Chrome()
        
        # go to Sogou news section, filter 1 year time period
        search_url = 'https://www.sogou.com/sogou?ie=utf8&interation=1728053249&query=' + self.search_query + '&tsn=4&sourceid=inttime_year'
        driver.get(search_url)
        
        # ----------------- Get all headlines -----------------
        headlines_list = []
        headlines = driver.find_elements_by_xpath('//h3/a')
        for headline in headlines:
            headlines_list.append(headline.text)
        
        
        # ----------------- Get all URLs -----------------
        links_list = [] # collect sogou links -- they redirect to the actual article
        for link in headlines:
            url = link.get_attribute('href')
            links_list.append(url)

        final_links_list = [] # final, redirected links
        for url in links_list:
            http = urllib3.PoolManager()
            response = http.request('GET', url)

            soup = BeautifulSoup(response.data)
            raw_dest_url = soup.find('script')
            dest_url = re.search(r'\("(.+)"\)', raw_dest_url.string).group(1)

            final_links_list.append(dest_url)
            
        
        # ----------------- Get all snippets  -----------------
        summaries_list = []
        summaries = driver.find_elements_by_xpath("//p[@class='star-wiki']")
        for summary in summaries:
            summaries_list.append(summary.text)
            
        # ----------------- Get all sources dates -----------------
        raw_source_list = driver.find_elements_by_xpath("//p[@class='news-from text-lightgray']/span[1]")
         
        translator = google_translator()    
        source_list = []
        for source in raw_source_list:
            if hanzidentifier.has_chinese(source.text):
                trans_source = translator.translate(source.text, lang_tgt='en')
                time.sleep(3)
                source_list.append(trans_source)
            else:
                raw_source = source.text
                source_list.append(raw_source)
        
        
        # ----------------- Get all selected dates -----------------
        dates = driver.find_elements_by_xpath("//p[@class='news-from text-lightgray']/span[2]")
        dates_list = [] # keep all dates
        dates_index = [] # only keep index of dates we want
        for i in range(len(dates)):
            
            if hanzidentifier.has_chinese(dates[i].text):
                try:
                    raw_date = dates[i].text[:-1]
                    string_date = re.sub('[^0-9]', '-', raw_date) # date in YYYY-m-d format
                    format_date = datetime.datetime.strptime(string_date, '%Y-%m-%d').date()
                    dates_list.append(format_date)
                except:
                    continue
            else: 
                dates_list.append(dates[i].text)

            if self.end_date >= format_date >= self.start_date: # filter out for time period specified
                dates_index.append(i)
        
        # ----------------- Pull selected Articles -----------------
        if len(dates_index) > 0:
            articles_list = []
            for index in dates_index:
                try:
                    article_dict = {}
                    article_url = final_links_list[index]

                    article = Article(article_url, language = 'zh')
                    article.download()
                    article.parse()
                    article_dict['Search Query'] = self.search_query
                    article_dict['Date'] = dates_list[index]
                    article_dict['Source'] = source_list[index]
                    article_dict['URL'] = final_links_list[index]
                    
                    translator = google_translator()
                    raw_title = headlines_list[index]
                    article_dict['Title'] = translator.translate(raw_title, lang_tgt='en')
                    time.sleep(3)
                    
                    # use snippets if article.text is empty or article.text is too long (> 5000 characters) for translation
                    if article.text == '' or len(article.text) > 5000:
                        raw_summary = summaries_list[index]
                        article_dict['Article'] = translator.translate(raw_summary, lang_tgt='en')
                        time.sleep(3)
                    else:
                        raw_article = re.sub('\n\n', ' ', article.text)
                        article_dict['Article'] = translator.translate(raw_article, lang_tgt='en')
                        time.sleep(3)

                    articles_list.append(article_dict)
                except:
                    continue

            articles_df = pd.DataFrame(articles_list)
                            
        else:
            articles_df = pd.DataFrame({
                'Search Query': self.search_query,
                'Date': [np.nan],
                'Source': [np.nan],
                'URL': [np.nan],
                'Title': [np.nan],
                'Article': [np.nan]
            })
        
        
        driver.quit()
        
        return articles_df


# In[56]:


articles = SogouNewsDownloader(search_query = '星糖miniKTV', start_date = one_year_ago, end_date = start_date)
df = articles.get_news_articles()


# In[57]:


df


# In[ ]:





# ## Pull Google News

# In[49]:


class GoogleNewsDownloader:
    def __init__(self, search_query, start_date, end_date):
        self.search_query = search_query
        self.start_date = start_date.strftime("%m-%d-%Y")
        self.end_date = end_date.strftime("%m-%d-%Y")
        self.black_list_sites = ["Bloomberg"]

    def get_news_articles(self, search_query):
        try:
            googlenews = GoogleNews(start=self.start_date, end=self.end_date) # GoogleNews dates to be in MM-DD-YYYY
            googlenews.search(self.search_query)
            result = googlenews.result()
            news = pd.DataFrame(result)
            list_of_articles = []
            for ind in news.index:
                try:
                    article_dict={}
                    article = Article(news['link'][ind])
                    article.download()
                    article.parse()
                    article.nlp()
                    article_dict['Search Query']=self.search_query
                    article_dict['Date']=article.publish_date
                    
                    if news['media'][ind] == '':
                        url = get_tld(news['link'][ind], as_object=True)
                        article_dict['Media'] = url.domain
                    else:
                        article_dict['Media']=news['media'][ind]
                        
                    article_dict['URL']=news['link'][ind]
                    article_dict['Title']= re.sub('\n\n', ' ', article.title)
                    article_dict['Article']= re.sub('\n\n', ' ', article.text)
                    article_dict['Summary']=article.summary
                    if article_dict['Article'] and article_dict['Media'] not in self.black_list_sites:
                        list_of_articles.append(article_dict)
                except:
                    continue
            return list_of_articles
        except Exception as e:
            print(e)


    # with no ring fencing - allintext looks for company mention in the news article
    def download_news(self, **kwargs):
        if "location" in kwargs:
            search_query = "{} location:{}".format(
                self.search_query, kwargs["location"])
            result = self.get_news_articles(search_query)
            return result
        
        elif "site" in kwargs:
            search_query = "{} site:{}".format(
                self.search_query, kwargs["site"])
            result = self.get_news_articles(search_query)
            return result
        
        else:
            search_query = "allintext:{}".format(self.search_query)
            result = self.get_news_articles(search_query)
            return result


# In[ ]:




