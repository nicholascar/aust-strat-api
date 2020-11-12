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


def get_strat_unit(strat_unit_id, return_original_xml=False):
    # ?service=WFS&version=2.0.0&request=GetFeature&typeName=gsmlb%3AGeologicUnit&featureid=asud.gsml.geologicunit.332
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "gsmlb:GeologicUnit",
        "featureid": "asud.gsml.geologicunit.{}".format(strat_unit_id.lstrip("GA.GeologicProvince.")),
    }

    headers = {'Content-Type': 'application/xml'}
    r = requests.get(
        "http://stratunits.gs.cloud.ga.gov.au/gsmlb/wfs",
        params=params,
        headers=headers
    )
    if return_original_xml:
        return r.text

    tree = etree.fromstring(r.content)
    namespaces = {
        "gml": "http://www.opengis.net/gml/3.2",  # "http://www.opengis.net/gml",
        "gsmlb": "http://www.opengis.net/gsml/4.1/GeoSciML-Basic",
        "swe": "http://www.opengis.net/swe/2.0",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    descriptionpurposes = {
        "definingNorm": ("http://resource.geosciml.org/classifier/cgi/descriptionpurpose/defining_norm", "defining norm"),
        "instance": ("http://resource.geosciml.org/classifier/cgi/descriptionpurpose/instance", "instance"),
        "typicalNorm": ("http://resource.geosciml.org/classifier/cgi/descriptionpurpose/typical_norm", "typical norm")
    }
    descriptionPurpose = safe_list_get(tree.xpath('//gsmlb:purpose/text()', namespaces=namespaces), 0, None)
    if descriptionPurpose is not None:
        descriptionPurpose = descriptionpurposes[descriptionPurpose]

    eventProcess = None
    youngerBound = None
    olderBound = None
    youngerNamedAge = None
    olderNamedAge = None

    geologicHistory = safe_list_get(tree.xpath('//gsmlb:geologicHistory/gsmlb:GeologicEvent', namespaces=namespaces), 0, None)
    if geologicHistory is not None:
        if safe_list_get(geologicHistory.xpath("//gsmlb:eventProcess", namespaces=namespaces), 0, None) is not None:
            eventProcess = (
                safe_list_get(geologicHistory.xpath("gsmlb:eventProcess/@xlink:href", namespaces=namespaces), 0, None),
                safe_list_get(geologicHistory.xpath("gsmlb:eventProcess/@xlink:title", namespaces=namespaces), 0, None),
            )

        if safe_list_get(geologicHistory.xpath("//gsmlb:youngerBoundDate", namespaces=namespaces), 0, None) is not None:
            youngerBound = (
                safe_list_get(tree.xpath("//gsmlb:youngerBoundDate/swe:Quantity/swe:value/text()", namespaces=namespaces), 0, None),
                safe_list_get(tree.xpath("//gsmlb:youngerBoundDate/swe:Quantity/swe:uom/@xlink:href", namespaces=namespaces), 0, None),
                safe_list_get(tree.xpath("//gsmlb:youngerBoundDate/swe:Quantity/swe:uom/@xlink:title", namespaces=namespaces), 0, None),
            )

        if safe_list_get(geologicHistory.xpath("//gsmlb:olderBoundDate", namespaces=namespaces), 0, None) is not None:
            olderBound = (
                safe_list_get(tree.xpath("//gsmlb:olderBoundDate/swe:Quantity/swe:value/text()", namespaces=namespaces), 0, None),
                safe_list_get(tree.xpath("//gsmlb:olderBoundDate/swe:Quantity/swe:uom/@xlink:href", namespaces=namespaces), 0, None),
                safe_list_get(tree.xpath("//gsmlb:olderBoundDate/swe:Quantity/swe:uom/@xlink:title", namespaces=namespaces), 0, None),
            )

        if safe_list_get(geologicHistory.xpath("//gsmlb:youngerNamedAge", namespaces=namespaces), 0, None) is not None:
            youngerNamedAge = (
                safe_list_get(geologicHistory.xpath("//gsmlb:youngerNamedAge/@xlink:href", namespaces=namespaces), 0, None),
                safe_list_get(geologicHistory.xpath("//gsmlb:youngerNamedAge/@xlink:title", namespaces=namespaces), 0, None),
            )

        if safe_list_get(geologicHistory.xpath("//gsmlb:olderNamedAge", namespaces=namespaces), 0, None) is not None:
            olderNamedAge = (
                safe_list_get(geologicHistory.xpath("//gsmlb:olderNamedAge/@xlink:href", namespaces=namespaces), 0, None),
                safe_list_get(geologicHistory.xpath("//gsmlb:olderNamedAge/@xlink:title", namespaces=namespaces), 0, None),
            )

    return {
        "uri": tree.xpath('//gml:identifier/text()', namespaces=namespaces)[0],
        "title": tree.xpath('//gml:name/text()', namespaces=namespaces)[0],
        "description": safe_list_get(tree.xpath('//gml:description/text()', namespaces=namespaces), 0, None),
        "observationMethod": (
            tree.xpath("//gsmlb:observationMethod/@xlink:href", namespaces=namespaces)[0],
            tree.xpath("//gsmlb:observationMethod/@xlink:title", namespaces=namespaces)[0],
        ),
        "descriptionPurpose": descriptionPurpose,
        "geologicUnitType": (
            tree.xpath("//gsmlb:geologicUnitType/@xlink:href", namespaces=namespaces)[0],
            tree.xpath("//gsmlb:geologicUnitType/@xlink:title", namespaces=namespaces)[0]
        ),
        "stratigraphicRank": (
            tree.xpath("//gsmlb:rank/@xlink:href", namespaces=namespaces)[0],
            tree.xpath("//gsmlb:rank/@xlink:title", namespaces=namespaces)[0]
        ),
        "eventProcess": eventProcess,
        "youngerBound": youngerBound,
        "olderBound": olderBound,
        "youngerNamedAge": youngerNamedAge,
        "olderNamedAge": olderNamedAge,
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
    # with open("1001.xml", "w") as f:
    #     f.write(get_strat_unit("1001", return_original_xml=True))
    import pprint
    pprint.pprint(get_strat_unit("1001"))
    #
    # with open("10003.xml", "w") as f:
    #     f.write(get_strat_unit("10003", return_original_xml=True))

# http://pid.geoscience.gov.au/feature/id/ga/gsmlp/geologicunitview/28

# dataset <http://pid.geoscience.gov.au/dataset/ga/21884>

# Strat Unit: http://pid.geoscience.gov.au/geologicFeature/au/SU<stratno>

# Provinces:  http://pid.geoscience.gov.au/geologicFeature/au/PR<provno>

    # data = """
    #     <?xml version="1.0" ?>
    #     <wfs:GetFeature
    #        service="WFS"
    #        version="1.1.3"
    #        xmlns:wfs="http://www.opengis.net/wfs"
    #        xmlns:ogc="http://www.opengis.net/ogc"
    #        xmlns:gsmlb="http://www.opengis.net/gsml/4.1/GeoSciML-Basic"
    #        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    #        xsi:schemaLocation="http://www.opengis.net/wfs ../wfs/1.1.3/WFS.xsdwfs.xsd">
    #        <wfs:Query typeName="gsmlb:GeologicUnit">
    #           <wfs:PropertyName>gsmlb:purpose</wfs:PropertyName>
    #        </wfs:Query>
    #     </wfs:GetFeature>
    # """.strip()
    #
    # headers = {'Content-Type': 'application/xml'}
    # r = requests.post(
    #     "http://stratunits.gs.cloud.ga.gov.au/gsmlb/wfs",
    #     data=data,
    #     #headers=headers
    # )
    # print(r.text)
