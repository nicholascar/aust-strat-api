import requests
from lxml import etree
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import DCTERMS, RDF
from api.config import *
from os.path import *
import logging
from api.config import DATA_DIR


def get_no_of_stratunits():
    url = "http://stratunits.gs.cloud.ga.gov.au/stratunit/ows" \
            "?service=WFS" \
            "&request=GetFeature" \
            "&typeName=stratunit%3AStratigraphicUnit" \
            "&version=1.1.0" \
            "&resultType=hits"

    r = requests.get(url)

    return int(r.text.split("numberOfFeatures=\"", 1)[1].split("\"", 1)[0])


def store_stratunit_index(no_of_stratunits):
    r = requests.get(
        "http://stratunits.gs.cloud.ga.gov.au/stratunit/ows"
        "?service=WFS"
        "&version=1.0.0"
        "&request=GetFeature"
        "&typeName=stratunit%3AStratigraphicUnit"
        "&maxFeatures={}"
        "&propertyname=stratunit:name".format(no_of_stratunits)
    )

    tree = etree.fromstring(r.content)
    features = tree.xpath('//gml:featureMember', namespaces={"gml": "http://www.opengis.net/gml"})
    g = Graph()
    STRAT = Namespace("http://pid.geoscience.gov.au/def/stratunits#")
    GFS = Namespace("http://pid.geoscience.gov.au/geologicFeature/au/")
    g.bind("strat", STRAT)
    g.bind("gfs", GFS)
    g.bind("dcterms", DCTERMS)

    for feature in features:
        fid = "SU" + feature.xpath(
            './/stratunit:StratigraphicUnit/@fid', namespaces={"stratunit": "http://www.ga.gov.au/stratunit"}
        )[0].replace("StratigraphicUnit.", "")
        name = feature.xpath('.//stratunit:name/text()', namespaces={"stratunit": "http://www.ga.gov.au/stratunit"})[0]
        this_feature_uri = GFS[fid]
        g.add((
            this_feature_uri,
            RDF.type,
            STRAT.Unit
        ))
        g.add((
            this_feature_uri,
            DCTERMS.identifier,
            Literal(fid)
        ))
        g.add((
            this_feature_uri,
            DCTERMS.title,
            Literal(name)
        ))

    g.serialize(destination=os.path.join(DATA_DIR, "stratunits-index.ttl"), format="turtle")

    print("index stored")


def safe_list_get(ls, idx, default):
    try:
        return ls[idx]
    except IndexError:
        return default


def get_strat_unit(province_id):
    # ?service=WFS&version=2.0.0&request=GetFeature&typeName=gsmlb%3AGeologicUnit&featureid=asud.gsml.geologicunit.332
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "gsmlb:GeologicUnit",
        "featureid": "asud.gsml.geologicunit.{}".format(province_id),
    }

    headers = {'Content-Type': 'application/xml'}
    r = requests.get(
        "http://stratunits.gs.cloud.ga.gov.au/gsmlb/wfs",
        params=params,
        headers=headers
    )
    tree = etree.fromstring(r.content)
    namespaces = {
        "gml": "http://www.opengis.net/gml/3.2",  # "http://www.opengis.net/gml",
        "gsmlb": "http://www.opengis.net/gsml/4.1/GeoSciML-Basic",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    return {
        "title": tree.xpath('//gml:name/text()', namespaces=namespaces)[0],
        "observationMethod": tree.xpath("//gsmlb:observationMethod/@xlink:href", namespaces=namespaces)[0],
        "purpose": tree.xpath('//gsmlb:purpose/text()', namespaces=namespaces)[0],
        "geologicUnitType_uri": tree.xpath("//gsmlb:geologicUnitType/@xlink:href", namespaces=namespaces)[0],
        "geologicUnitType_prefLabel": tree.xpath("//gsmlb:geologicUnitType/@xlink:title", namespaces=namespaces)[0],
    }


if __name__ == "__main__":
    # n = get_no_of_provinces()
    # store_provinces_index(n)
    # # n = get_no_of_stratunits()
    # # store_stratunit_index(n)
    # # get_province("AllProvinces.3")
    # # import pprint
    # # pprint.pprint(get_province("GA.GeologicProvince.1"))

    # print(cache_timescale_types())
    print(get_strat_unit("10001"))


# http://pid.geoscience.gov.au/feature/id/ga/gsmlp/geologicunitview/28

# dataset <http://pid.geoscience.gov.au/dataset/ga/21884>

# Strat Unit: http://pid.geoscience.gov.au/geologicFeature/au/SU<stratno>

# Provinces:  http://pid.geoscience.gov.au/geologicFeature/au/PR<provno>