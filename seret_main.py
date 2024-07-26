import logging
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from retry import retry

from db import DB
from movie_model import MovieModel
from site_info_model import SiteInfoModel

SITEMAP_URL = 'https://www.seret.co.il/Sitemapsite.xml'

headers = {
    'User-Agent': 'Mozilla/5.0',
}


def get_sitemap(sitemap_url: str, session: requests.Session) -> bytes:
    res = session.get(sitemap_url)
    if res.status_code != 200:
        logging.error(f"Failed to get sitemap, status code: {res.status_code}")
    with open('sitemap.html', 'wb') as f:
        f.write(res.content)
    return res.content


@retry(Exception, tries=3, delay=10)
def get_sites(sitemap_url: str, session: requests.Session) -> list[SiteInfoModel]:
    sitemap = get_sitemap(sitemap_url, session)
    soup = BeautifulSoup(sitemap, "lxml")
    sites: list[SiteInfoModel] = []
    for site in soup.find_all("url"):
        url = site.find_next('loc').text
        if not url.startswith('https://www.seret.co.il/movies/s_movies.asp?MID='):
            continue
        mid = url.split('MID=')[-1]
        priority = float(site.find_next('priority').text)
        sites.append(SiteInfoModel(mid=mid, url=url, priority=priority))
    if not sites:
        raise Exception("Failed to get sites")
    logging.info(f"Found {len(sites)} sites")
    return sites


def filter_cached_sites(sites: list[SiteInfoModel], db: DB) -> list[SiteInfoModel]:
    cached = db.get_cached(sites)
    cached = {cache.mid: cache.priority for cache in cached}
    if cached:
        return [site for site in sites if
                site.mid not in cached.keys() or site.priority > 0.8
                or site.priority != cached[site.mid]]
    else:
        return sites


def handle_site(site: SiteInfoModel, session: requests.Session, movie_index: int, all_movies_len: int, db: DB):
    res = session.get(site.url)
    soup = BeautifulSoup(res.content, "html.parser")

    if soup.find("link", {"rel": "canonical"})['href'] != site.url:
        logging.warning(f"{site.url} is not canonical, skipping AND adding to cache")
        db.add_to_cache(site)
        return

    name = soup.find("meta", {"property": "og:title"})['content']
    english_name = soup.find("span", {"itemprop": "alternatename"}).text
    keywords = soup.find("meta", {"name": "keywords"})['content'].split(',')
    description = soup.find("span", {"itemprop": "description"})
    image_url = soup.find("meta", {"property": "og:image"})['content']

    raw_year = soup.find("span", {"itemprop": "dateCreated"})
    if raw_year and raw_year.text.isdigit():
        year = int(raw_year.text)
    else:
        logging.warning(f"Failed to get year for {site}")
        year = None
    raw_premiere = soup.find("span", {"itemprop": "datePublished"}).text.split(" ")[0]
    if raw_premiere:
        premiere = datetime.strptime(raw_premiere, "%d/%m/%Y")
    else:
        premiere = datetime(year=year, month=1, day=1)
        logging.warning(f"Failed to get premiere for {site}, setting to {premiere}")
    movie = MovieModel(id=site.mid, url=site.url, priority=site.priority, name=name, english_name=english_name,
                       keywords=keywords, description=description.text, image_url=image_url, year=year,
                       premiere=premiere)
    db.submit_movie(movie, movie_index, all_movies_len, site)


def main(db: DB, session: requests.Session):
    sites = get_sites(SITEMAP_URL, session)
    sites = filter_cached_sites(sites, db)
    sites.sort(key=lambda x: x.mid)

    all_movies_len = len(sites)
    logging.info(f"Found {all_movies_len} new sites")
    for i, site in enumerate(sites):
        try:
            handle_site(site, session, i + 1, all_movies_len, db)
        except Exception as e:
            logging.error(f"Failed to handle site {site}", exc_info=e)


if __name__ == '__main__':
    db = DB(logging.root)
    db.create_index()
    session = requests.Session()
    session.headers = headers
    if os.environ.get('CI'):  # Only set proxy in CI
        session.proxies = {'http': "127.0.0.1:8118", 'https': "127.0.0.1:8118"}
    main(db, session)
