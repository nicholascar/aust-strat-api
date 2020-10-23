from typing import List
from api.model.profiles import *
from api.config import *
from api.model.link import *
import json
from flask import Response, render_template
from rdflib import URIRef, Literal
from rdflib.namespace import DCTERMS, SKOS
import markdown



class Feature(object):
    def __init__(
            self,
            uri: str,
            other_links: List[Link] = None,
    ):
        self.uri = uri

        q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcapi/>

            SELECT ?identifier ?title ?description
            WHERE {{
                ?uri a ogcapi:Feature ;
                   dcterms:isPartOf <{}> ;
                   dcterms:identifier ?identifier ;
                   OPTIONAL {{?uri dcterms:title ?title}}
                   OPTIONAL {{?uri dcterms:description ?description}}
            }}
            """  # .format(collection_id)
        g = get_graph()
        # Feature properties
        self.description = None
        for p, o in g.predicate_objects(subject=URIRef(self.uri)):
            if p == DCTERMS.identifier:
                self.identifier = str(o)
            elif p == DCTERMS.title:
                self.title = str(o)
            elif p == DCTERMS.description:
                self.description = markdown.markdown(str(o))
            elif p == DCTERMS.isPartOf:
                self.isPartOf = str(o)

        # Feature geometries
        # out of band call for Geometries as BNodes not supported by SPARQLStore
        q = """
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            PREFIX geox: <https://linked.data.gov.au/def/geox#>
            SELECT * 
            WHERE {{
                <{}>
                    geo:hasGeometry/geo:asWKT ?g1 ;
                    geo:hasGeometry/geox:asDGGS ?g2 .
            }}
            """.format(self.uri)
        from SPARQLWrapper import SPARQLWrapper, JSON
        sparql = SPARQLWrapper(None)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        ret = sparql.queryAndConvert()["results"]["bindings"]
        self.geometries = [
            Geometry(ret[0]["g1"]["value"], GeometryRole.Boundary, "WGS84 Geometry", CRS.WGS84),
            Geometry(ret[0]["g2"]["value"], GeometryRole.Boundary, "TB16Pix Geometry", CRS.TB16PIX),
        ]

        # Feature other properties
        self.extent_spatial = None
        self.extent_temporal = None
        self.links = [
            Link(LANDING_PAGE_URL + "/collections/" + self.identifier + "/items",
                 rel=RelType.ITEMS.value,
                 type=MediaType.GEOJSON.value,
                 title=self.title)
        ]
        if other_links is not None:
            self.links.extend(other_links)

    def to_dict(self):
        self.links = [x.__dict__ for x in self.links]
        if self.geometries is not None:
            self.geometries = [x.to_dict() for x in self.geometries]
        return self.__dict__

    def to_geo_json_dict(self):
        # this only serialises the Feature properties and WGS84 Geometries
        """
        {
          "type": "Feature",
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
            ]
          },
        """
        geojson_geometry = [g.to_geo_json_dict() for g in self.geometries if g.crs == CRS.WGS84][0]  # one only

        properties = {
            "title": self.title,
            "isPartOf": self.isPartOf
        }
        if self.description is not None:
            properties["description"] = self.description

        return {
            "id": self.uri,
            "type": "Feature",
            "geometry": rewind(geojson_geometry),
            "properties": properties
        }

    def to_geosp_graph(self):
        g = Graph()
        g.bind("geo", GEO)
        g.bind("geox", GEOX)

        f = URIRef(self.uri)
        g.add((
            f,
            RDF.type,
            GEO.Feature
        ))
        for geom in self.geometries:
            this_geom = BNode()
            g.add((
                f,
                GEO.hasGeometry,
                this_geom
            ))
            g.add((
                this_geom,
                RDFS.label,
                Literal(geom.label)
            ))
            g.add((
                this_geom,
                GEOX.hasRole,
                URIRef(geom.role.value)
            ))
            g.add((
                this_geom,
                GEOX.inCRS,
                URIRef(geom.crs.value)
            ))
            if geom.crs == CRS.TB16PIX:
                g.add((
                    this_geom,
                    GEOX.asDGGS,
                    Literal(geom.coordinates, datatype=GEOX.DggsLiteral)
                ))
            else:  # WGS84
                g.add((
                    this_geom,
                    GEO.asWKT,
                    Literal(geom.coordinates, datatype=GEO.WktLiteral)
                ))

        return g


class Province(Feature):
    def __init__(
            self,
            uri: str,
            other_links: List[Link] = None,
    ):
        # make URI from ID
        self.uri = uri
        self.identifier = uri.split("/PR")[1]

        # get Province info from WFS
        from api.wfs_utils import get_province
        props = get_province("GA.GeologicProvince." + self.identifier)
        # Feature properties
        self.title = props["title"]
        self.description = props["description"] or "" + "\n\n" + props["overview"] or ""
        self.source = props["source"]
        self.type = None
        for s in get_graph().subjects(predicate=SKOS.notation, object=Literal(props["type"])):
            for o in get_graph().objects(subject=s, predicate=SKOS.prefLabel):
                self.type = (str(s), str(o))
        self.rank = None
        for s in get_graph().subjects(predicate=SKOS.notation, object=Literal(props["rank"])):
            for o in get_graph().objects(subject=s, predicate=SKOS.prefLabel):
                self.rank = (str(s), str(o))
        for o in get_graph().objects(subject=URIRef(props["older"]), predicate=SKOS.prefLabel):
            self.older = (props["older"], str(o))
        for o in get_graph().objects(subject=URIRef(props["younger"]), predicate=SKOS.prefLabel):
            self.younger = (props["younger"], str(o))
        self.parent_id = props["parent_id"]
        self.parent_name = props["parent_name"]
        self.bbox = props["bbox"]

        self.geometries = [
            Geometry(props["bbox"], GeometryType.Polygon, GeometryRole.BoundingBox, "WGS84 Bounding Box", CRS.WGS84),
            Geometry(props["coords"], GeometryType.Polygon, GeometryRole.Boundary, "WGS84 Boundary", CRS.WGS84),
        ]

        self.calculate_centroid()

        # Feature other properties
        self.extent_spatial = None
        self.extent_temporal = None
        self.links = [
            Link(LANDING_PAGE_URL + "/collections/agp/items",
                 rel=RelType.ITEMS.value,
                 type=MediaType.GEOJSON.value,
                 title=self.title)
        ]
        if other_links is not None:
            self.links.extend(other_links)

        self.isPartOf = "agp"

    def calculate_centroid(self):
        centroid = None
        for geometry in self.geometries:
            if geometry.role == GeometryRole.Boundary and geometry.crs == CRS.WGS84:
                p1 = load_wkt(geometry.to_wkt(with_crs=False))
                centroid = Geometry(p1.centroid.wkt.strip("POINT (").strip(")"), GeometryType.Point, GeometryRole.Centroid, "WGS84 Centroid", CRS.WGS84)
                self.geometries.append(centroid)

        return centroid


class FeatureRenderer(Renderer):
    def __init__(self, request, feature_uri: str, other_links: List[Link] = None):
        self.feature = Feature(feature_uri)
        self.links = []
        if other_links is not None:
            self.links.extend(other_links)

        super().__init__(
            request,
            LANDING_PAGE_URL + "/collections/" + self.feature.isPartOf + "/item/" + self.feature.identifier,
            profiles={"oai": profile_openapi, "geosp": profile_geosparql},
            default_profile_token="oai"
        )

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype"]

    def render(self):
        for v in self.request.values.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response("The parameter {} you supplied is not allowed".format(v[0]), status=400)

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype == MediaType.JSON.value:
                return self._render_oai_json()
            elif self.mediatype == MediaType.GEOJSON.value:
                return self._render_oai_geojson()
            else:
                return self._render_oai_html()
        elif self.profile == "geosp":
            return self._render_geosp_rdf()

    def _render_oai_json(self):
        page_json = {
            "links": [x.__dict__ for x in self.links],
            "feature": self.feature.to_geo_json_dict()
        }

        return Response(
            json.dumps(page_json),
            mimetype=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_geojson(self):
        page_json = self.feature.to_geo_json_dict()
        if len(self.links) > 0:
            page_json["links"] = [x.__dict__ for x in self.links]

        return Response(
            json.dumps(page_json),
            mimetype=str(MediaType.GEOJSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        self.feature.geometries = [(x.coordinates, x.to_wkt(), x.type, x.role, x.label, x.crs) for x in self.feature.geometries]

        map_centroid = None
        map_bbox = []
        map_polygon = []
        for i, v in enumerate(self.feature.geometries):
            if v[3] == GeometryRole.Boundary:
                coords = [float(x) for x in v[0].split(" ")]
                for i2 in range(0, len(coords), 2):
                    map_polygon.append([coords[i2+1], coords[i2]])
            elif v[3] == GeometryRole.Centroid:
                map_centroid = [float(x) for x in reversed(v[0].split(" "))]
            elif v[3] == GeometryRole.BoundingBox:
                coords = [float(x) for x in v[0].split(" ")]
                for i2 in range(0, len(coords), 2):
                    map_bbox.append([coords[i2+1], coords[i2]])

        _template_context = {
            "links": self.links,
            "feature": self.feature,
            "map_centroid": map_centroid,
            "map_polygon": map_polygon,
            "map_bbox": map_bbox
        }

        return Response(
            render_template("feature.html", **_template_context),
            headers=self.headers,
        )

    def _render_geosp_rdf(self):
        g = self.feature.to_geosp_graph()

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        elif self.mediatype in Renderer.RDF_MEDIA_TYPES:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status=400,
                mimetype="text/plain"
            )


class ProvincesRenderer(FeatureRenderer):
    def __init__(self, request, feature_uri: str, other_links: List[Link] = None):
        self.feature = Province(feature_uri)
        self.links = []
        if other_links is not None:
            self.links.extend(other_links)

        super(FeatureRenderer, self).__init__(
            request,
            LANDING_PAGE_URL + "/collections/" + self.feature.isPartOf + "/item/" + self.feature.identifier,
            profiles={
                "oai": profile_openapi,
                "geosp": profile_geosparql,
                "loop3d": profile_loop3d,
                "su": profile_su
            },
            default_profile_token="oai"
        )

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype"]

    def render(self):
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "su":
            return self._render_su_rdf()

    def _render_su_rdf(self):
        g = self.feature.to_geosp_graph()
        g.bind("dcterms", DCTERMS)
        SU = Namespace("http://pid.geoscience.gov.au/def/stratunits#")
        g.bind("su", SU)
        ISC = Namespace("http://resource.geosciml.org/classifier/ics/ischart/")
        g.bind("isc", ISC)
        f = URIRef(self.feature.uri)

        g.add((
            f,
            SU.type,
            Literal(self.feature.type)
        ))

        g.add((
            f,
            SU.rank,
            Literal(self.feature.rank[0])
        ))

        g.add((
            f,
            SU.older,
            URIRef(self.feature.older[0])
        ))

        g.add((
            URIRef(self.feature.older[0]),
            SKOS.prefLabel,
            Literal(self.feature.older[1])
        ))

        g.add((
            f,
            SU.younger,
            URIRef(self.feature.younger[0])
        ))

        g.add((
            URIRef(self.feature.younger[0]),
            SKOS.prefLabel,
            Literal(self.feature.younger[1])
        ))

        g.add((
            f,
            DCTERMS.source,
            Literal(self.feature.source)
        ))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        elif self.mediatype in Renderer.RDF_MEDIA_TYPES:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status=400,
                mimetype="text/plain"
            )

    def _render_oai_html(self):
        self.feature.geometries = [(x.coordinates, x.to_wkt(), x.type, x.role, x.label, x.crs) for x in self.feature.geometries]

        map_centroid = None
        map_bbox = []
        map_polygon = []
        for i, v in enumerate(self.feature.geometries):
            if v[3] == GeometryRole.Boundary:
                coords = [float(x) for x in v[0].split(" ")]
                for i2 in range(0, len(coords), 2):
                    map_polygon.append([coords[i2+1], coords[i2]])
            elif v[3] == GeometryRole.Centroid:
                map_centroid = [float(x) for x in reversed(v[0].split(" "))]
            elif v[3] == GeometryRole.BoundingBox:
                coords = [float(x) for x in v[0].split(" ")]
                for i2 in range(0, len(coords), 2):
                    map_bbox.append([coords[i2+1], coords[i2]])

        _template_context = {
            "links": self.links,
            "feature": self.feature,
            "map_centroid": map_centroid,
            "map_polygon": map_polygon,
            "map_bbox": map_bbox
        }

        return Response(
            render_template("province.html", **_template_context),
            headers=self.headers,
        )