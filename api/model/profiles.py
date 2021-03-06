from pyldapi.profile import Profile
from pyldapi.renderer import Renderer


profile_openapi = Profile(
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/req/oas30",
    label="OpenAPI 3.0",
    comment="The OpenAPI Specification (OAS) defines a standard, language-agnostic interface to RESTful APIs which "
            "allows both humans and computers to discover and understand the capabilities of the service without "
            "access to source code, documentation, or through network traffic inspection.",
    mediatypes=["text/html", "application/geo+json", "application/json"],
    default_mediatype="application/geo+json",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_dcat = Profile(
    "https://www.w3.org/TR/vocab-dcat/",
    label="DCAT",
    comment="Dataset Catalogue Vocabulary (DCAT) is a W3C-authored RDF vocabulary designed to "
    "facilitate interoperability between data catalogs "
    "published on the Web.",
    mediatypes=["text/html", "application/json"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_geosparql = Profile(
    "http://www.opengis.net/ont/geosparql",
    label="GeoSPARQL",
    comment="An RDF/OWL vocabulary for representing spatial information",
    mediatypes=Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_agp = Profile(
    "http://services.ga.gov.au:80/gis/services/Australian_Geological_Provinces/MapServer/WFSServer?service=wfs%26version=1.1.0%26request=DescribeFeatureType",
    label="Australian Geological Provinces WFS",
    comment="A GML-based XML schema for representing Australian_Geological_Provinces' information",
    mediatypes=["text/xml"],
    default_mediatype="text/xml",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_su = Profile(
    "http://pid.geoscience.gov.au/def/stratunits#",
    label="Stratigraphic Units Ontology",
    comment="A basic OWL ontology for conveying Stratigraphic Unit information",
    mediatypes=Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_loop3d = Profile(
    "http://example.com/ont/loop",
    label="Loop3D Ontology",
    comment="A fancy ontology for conveying Stratigraphic Unit information",
    mediatypes=Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_gsmlb = Profile(
    "http://www.opengis.net/gsml/4.1/GeoSciML-Basic",
    label="GeoSciML Basic",
    comment="GeoSciML describes geological features from the mapping perspective, articulated around the concept of "
            "a MappedFeature ??? the cartographic element shown on a map, and the GeologicFeature it represents. All "
            "geologic concepts that can be represented on a map are subtypes of GeologicFeature.",
    mediatypes=["application/xml"],
    default_mediatype="application/xml",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)
