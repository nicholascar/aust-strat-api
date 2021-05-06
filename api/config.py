import os
from rdflib import Graph, Namespace, BNode
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from pathlib import Path
import logging
import pickle

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "view" / "templates"
STATIC_DIR = APP_DIR / "view" / "style"
LOGFILE = APP_DIR / "ogcapild.log"
DEBUG = True
PORT = os.environ.get("PORT", 5000)
CACHE_HOURS = os.environ.get("CACHE_HOURS", 1)
CACHE_FILE = APP_DIR / "cache" / "DATA.pickle"
LOCAL_URIS = os.environ.get("LOCAL_URIS", True)

GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEOX = Namespace("https://linked.data.gov.au/def/geox#")
OGCAPI = Namespace("https://data.surroundaustralia.com/def/ogcapi/")
LANDING_PAGE_URL = "http://localhost:{}".format(PORT)
API_TITLE = "OGC LD API"
VERSION = "1.1"

DATASET_URI = "http://pid.geoscience.gov.au/dataset/ga/21884"
DATA_DIR = APP_DIR.parent / "data"


def get_graph():
    if Path.is_file(CACHE_FILE):  # and not DEBUG:
        logging.debug("reading from cache")
        with open(CACHE_FILE, "rb") as f:
            g = pickle.load(f)
    else:
        logging.debug("writing cache")
        g = Graph()
        for f in DATA_DIR.glob("**/*.ttl"):
            g.parse(f)
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(g, f)

    return g
