import logging
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from retry import retry

from db import DB
from movie_model import MovieModel
from site_info_model import SiteInfoModel

BASE_URL = "https://www.edb.co.il"
SEARCH_PAGE = "https://www.edb.co.il/browse/browse.php?type[]=1&type[]=2&type[]=5&type[]=6&order_by=year,asc&view=quick&view_count=100&"

headers = {
    'User-Agent': 'Mozilla/5.0',
}


def parse_search_page(soup: BeautifulSoup, priority: float) -> list[SiteInfoModel]:
    main_container = soup.find("main", {"id": "main-container"})
    raw_sites = main_container.find_all("li")
    sites = []
    for site in raw_sites:
        url = BASE_URL + site.find("a")['href']
        mid = url.split("/title/")[1].split("/")[0]
        sites.append(SiteInfoModel(mid=mid, url=url, priority=priority))
    return sites


@retry(Exception, tries=3, delay=10)
def get_sites(search_page: str, session: requests.Session, start_page: int = 1) -> list[SiteInfoModel]:
    sites = []
    res = session.get(search_page + f"&page={start_page}")
    soup = BeautifulSoup(res.text, "html.parser")
    total_pages = int(soup.find("span", {"class": "last"}).find("a")["href"].split("page=")[1].split('"')[0])
    logging.info(f"Found {total_pages} pages")
    parsed = parse_search_page(soup, 0.9 if total_pages - start_page < 3 else 0.8)
    sites.extend(parsed)
    logging.info(f"Found {len(parsed)} sites on page {start_page}/{total_pages}, total: {len(sites)}")

    for page in range(start_page + 1, total_pages + 1):
        res = session.get(search_page + f"&page={page}")
        soup = BeautifulSoup(res.text, "lxml")
        parsed = parse_search_page(soup, 0.9 if total_pages - page - 1 < 3 else 0.8)
        sites.extend(parsed)
        logging.info(f"Found {len(parsed)} sites on page {page}/{total_pages}, total: {len(sites)}")

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

    if soup.find("link", {"rel": "canonical"})['href'] != site.url.replace(BASE_URL, ""):
        logging.warning(f"{site.url} is not canonical, skipping AND adding to cache")
        db.add_to_cache(site)
        return

    titles = soup.find("div", {"class": "tpgfocusmain"})

    name = titles.find("h1", {"itemprop": "name"}).contents[0].text.strip()
    english_name = titles.find("h2").text.strip()
    keywords = soup.find("meta", {"name": "keywords"})['content'].split(',')
    descriptions = soup.find_all("div", {"class": "par_ind"})
    description = "לא נמצא תיאור" if not descriptions else descriptions[-1].text.strip()
    image_url = soup.find("meta", {"property": "og:image"})['content']
    image_url = None if image_url == "https://www.edb.co.il/static/images/edb_symbol.gif" else image_url

    raw_year = titles.find("h1", {"itemprop": "name"}).find("span")
    if raw_year and raw_year.text.strip("()").isdigit():
        year = int(raw_year.text.strip("()"))
    else:
        logging.warning(f"Failed to get year for {site}")
        year = None

    raw_premiere_section = soup.find(string=re.compile(".*הפצה רשמית.*")).parent
    raw_premiere = re.search("\d{2}\.\d{2}\.\d{4}", raw_premiere_section.text)
    if raw_premiere:
        premiere = datetime.strptime(raw_premiere.group(), "%d.%m.%Y")
    else:
        premiere = datetime(year=year, month=1, day=1)
        logging.warning(f"Failed to get premiere for {site}, setting to {premiere}")
    movie = MovieModel(id=site.mid, url=site.url, priority=site.priority, name=name, english_name=english_name,
                       keywords=keywords, description=description, image_url=image_url, year=year,
                       premiere=premiere)
    db.submit_movie(movie, movie_index, all_movies_len, site)


def main(db: DB, session: requests.Session):
    sites = get_sites(SEARCH_PAGE, session, 1)
    sites = filter_cached_sites(sites, db)

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
    # if os.environ.get('CI'):  # Only set proxy in CI
    #     session.proxies = {'http': "127.0.0.1:8118", 'https': "127.0.0.1:8118"}
    main(db, session)
