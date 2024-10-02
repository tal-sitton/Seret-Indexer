<style>
  a,
  a:hover,
  a:focus,
  a:active {
    text-decoration: none;
    color: #009cff;
  }
</style>

Seret Indexer is a Python-based web scraping and search project that fetches movie data
from [seret.co.il](https://www.seret.co.il) and from [edb.co.il](https://edb.co.il/) and indexes it into Elasticsearch
for offline and efficient searching.

It uses Github Actions to run the indexer periodically and save the data to Docker images.

## Searching

The results can be found in the docker image `ghcr.io/tal-sitton/seret-search:latest`.

So all you need to do is run the following command:

```docker
docker network create -d bridge elastic-net
docker run -p 9200:9200 --network elastic-net ghcr.io/tal-sitton/seret-search:latest
docker run -p 5601:5601 --network elastic-net docker.elastic.co/kibana/kibana:8.0.0
```

and you can access the elastic in port 9200, and the kibana in port 5601.

## To run it yourself:

### Prerequisites

- Python 3.11
- Elasticsearch 8.13.0
- Docker

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/tal-sitton/seret-indexer
   ```
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

### Usage

* Note that in the docker-compose file there is a service for proxy-vpn, this is only required for the github actions
  to run, and is not needed when running the program locally.

1. Start the Elasticsearch (and if you want, the Kibana) services using Docker Compose:
   ```
   docker compose -f elastic/docker-compose.yml up -d elasticsearch kibana
   ```
2. Run the main Python script:
   ```
   python main.py
   ```

### Project Structure

- [`seret_main.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/seret_main.py): The main script that fetches the sitemap, filters the cached sites, and handles each
  site. for seret.co.il
- [`edb_main.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/edb_main.py): The main script that fetches all the movies, filters the cached ones, and handles each
  site. for edb.co.il
- [`main.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/main.py): The main script that runs the seret_main.py and edb_main.py
- [`db.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/db.py): Contains the `DB` class for interacting with Elasticsearch.
- [`movie_model.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/movie_model.py) and [`site_info_model.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/site_info_model.py): Pydantic models for Movie and
  SiteInfo data.
- [`mappings.py`](https://github.com/tal-sitton/Seret-Indexer/blob/master/mappings.py): Contains the Elasticsearch mapping for the movie data.
- [`elastic/setup-data.sh`](https://github.com/tal-sitton/Seret-Indexer/blob/master/elastic/setup-data.sh) and [`elastic/dockerfile`](https://github.com/tal-sitton/Seret-Indexer/blob/master/elastic/dockerfile): Setup and Dockerfile
  for the Elasticsearch service.
- [`.github/workflows/app.yml`](https://github.com/tal-sitton/Seret-Indexer/blob/master/.github/workflows/app.yml): GitHub Actions workflow for running the program, committing
  and pushing Docker images,
  and saving logs and sitemap artifacts.
