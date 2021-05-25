from __future__ import print_function

import pandas as pd
import re
from tld import get_tld

import GoogleNews
from newspaper import Article

class NewsDownloader:
    def __init__(self, search_query, start_date, end_date):
        self.search_query = search_query
        self.start_date = start_date.strftime("%m-%d-%Y")
        self.end_date = end_date.strftime("%m-%d-%Y")
        self.black_list_sites = ["Bloomberg"]

    def get_news_articles(self, search_query):
        try:
            googlenews = GoogleNews(start=self.start_date, end=self.end_date)  # GoogleNews dates to be in MM-DD-YYYY
            googlenews.search(self.search_query)
            result = googlenews.result()
            news = pd.DataFrame(result)
            list_of_articles = []
            for ind in news.index:
                try:
                    article_dict = {}
                    article = Article(news['link'][ind])
                    article.download()
                    article.parse()
                    article.nlp()
                    article_dict['Seach Query'] = self.search_query
                    article_dict['Date'] = article.publish_date

                    if news['media'][ind] == '':
                        url = get_tld(news['link'][ind], as_object=True)
                        article_dict['Media'] = url.domain
                    else:
                        article_dict['Media'] = news['media'][ind]

                    article_dict['URL'] = news['link'][ind]
                    article_dict['Title'] = re.sub('\n\n', ' ', article.title)
                    article_dict['Article'] = re.sub('\n\n', ' ', article.text)
                    article_dict['Summary'] = article.summary
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
                self.company_name, kwargs["location"])
            result = self.get_news_articles(search_query)
            return result

        elif "site" in kwargs:
            search_query = "{} site:{}".format(
                self.company_name, kwargs["site"])
            result = self.get_news_articles(search_query)
            return result

        else:
            search_query = "allintext:{}".format(self.search_query)
            result = self.get_news_articles(search_query)
            return result

# In[29]:
