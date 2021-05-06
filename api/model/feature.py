from typing import List
from api.model.profiles import *
from api.config import *
from api.model.link import *
from flask import Response, render_template
from rdflib import URIRef, Literal
from rdflib.namespace import DCTERMS, SKOS, XSD
from api.wfs_utils import get_strat_unit


class StratUnit:
    def __init__(
            self,
            uri: str,
            other_links: List[Link] = None,
    ):
        # make URI from ID
        self.uri = uri
        self.identifier = uri.split("/SU")[1]

        # get Strat Unit info from WFS
        props = get_strat_unit("GA.GeologicProvince." + self.identifier)

        # Strat Unit properties
        for k, v in props.items():
            setattr(self, k, v)

        # Feature other properties
        self.links = [
            Link(LANDING_PAGE_URL + "/collections/sus/items",  # TODO: remove magic var 'sus'
                 rel=RelType.ITEMS.value,
                 type=MediaType.JSON.value,
                 title=self.title)
        ]
        if other_links is not None:
            self.links.extend(other_links)

        self.isPartOf = "http://example.com/dataset/auststrat/sus"  # TODO: remove magic var

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

        g.add((
            f,
            DCTERMS.isPartOf,
            URIRef(self.isPartOf)
        ))

        # TODO: add in relations to Provinces

        return g

    def to_su_graph(self):
        g = self.to_geosp_graph()
        g.bind("dcterms", DCTERMS)
        SU = Namespace("https://linked.data.gov.au/def/su/")
        g.bind("su", SU)
        ISC = Namespace("http://resource.geosciml.org/classifier/ics/ischart/")
        g.bind("isc", ISC)
        QUDT = Namespace("http://qudt.org/schema/qudt/")
        g.bind("qudt", QUDT)
        SUH = Namespace("http://pid.geoscience.gov.au/def/voc/stratigraphichierarchy/")
        g.bind("suh", SUH)

        f = URIRef(self.uri)

        if self.observationMethod is not None:
            g.add((
                f,
                SU.observationMethod,
                URIRef(self.observationMethod[0])
            ))

        if self.geologicUnitType is not None:
            g.add((
                f,
                SU.geologicUnitType,
                URIRef(self.geologicUnitType[0])
            ))

        if self.descriptionPurpose is not None:
            g.add((
                f,
                SU.descriptionPurpose,
                URIRef(self.descriptionPurpose[0])
            ))

        if self.stratigraphicRank is not None:
            g.add((
                f,
                SU.stratigraphicRank,
                URIRef(self.stratigraphicRank[0])
            ))

        # event stuff
        if self.eventProcess is not None or self.youngerBound is not None or self.youngerNamedAge is not None:
            ge = BNode()
            g.add((
                f,
                SU.geologicHistory,
                ge
            ))

        if self.eventProcess is not None:
            g.add((
                ge,
                SU.eventProcess,
                URIRef(self.eventProcess[0])
            ))

        if self.youngerBound is not None:
            yb = BNode()
            g.add((
                yb,
                RDF.type,
                QUDT.Quantity
            ))
            g.add((
                yb,
                QUDT.value,
                Literal(
                    float(self.youngerBound[0]) * 1000000
                    if self.youngerBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                    else self.youngerBound[0]
                    , datatype=XSD.float
                )
            ))
            g.add((
                yb,
                QUDT.units,
                URIRef(
                    "http://qudt.org/vocab/unit/YR"
                    if self.youngerBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                    else self.youngerBound[1]
                )
            ))
            g.add((
                ge,
                SU.youngerBound,
                yb
            ))

        if self.olderBound is not None:
            ob = BNode()
            g.add((
                ob,
                RDF.type,
                QUDT.Quantity
            ))
            g.add((
                ob,
                QUDT.value,
                Literal(
                    float(self.olderBound[0]) * 1000000
                    if self.olderBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                    else self.olderBound[0]
                    , datatype=XSD.float
                )
            ))
            g.add((
                ob,
                QUDT.units,
                URIRef(
                    "http://qudt.org/vocab/unit/YR"
                    if self.olderBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                    else self.olderBound[1]
                )
            ))
            g.add((
                ge,
                SU.olderBound,
                ob
            ))

        if self.youngerNamedAge is not None:
            g.add((
                ge,
                SU.youngerNamedAge,
                URIRef(self.youngerNamedAge[0])
            ))

        if self.olderNamedAge is not None:
            g.add((
                ge,
                SU.olderNamedAge,
                URIRef(self.olderNamedAge[0])
            ))

        for hl in self.hierarchyLinks:
            g.add((
                f,
                URIRef(hl["role"][0]),
                URIRef(hl["targetUnit"][0])
            ))

        return g

    def to_loop3d_graph(self):
        g = Graph()
        GSOC = Namespace("http://loop3d.org/GSO/ontology/2020/1/common/")
        g.bind("gsoc", GSOC)
        GSOG = Namespace("http://loop3d.org/GSO/ontology/2020/1/geologicfeature/")
        g.bind("gsog", GSOG)
        GSPR = Namespace("http://loop3d.org/GSO/ontology/2020/1/geologicprocess/")
        g.bind("gspr", GSPR)
        f = URIRef(self.uri)
        g.add((
            f,
            RDF.type,
            GSOG.Group
        ))
        # event stuff
        if self.eventProcess is not None or self.youngerBound is not None or self.youngerNamedAge is not None:
            QUDT = Namespace("http://qudt.org/schema/qudt/")
            g.bind("qudt", QUDT)

            LUNIT = Namespace("http://loop3d.org/GSO/ontology/2020/1/uom/")
            g.bind("lunit", LUNIT)

            EP = Namespace("http://resource.geosciml.org/classifier/cgi/eventprocess/")
            ge = BNode()
            g.add((
                ge,
                RDF.type,
                GSOG.Geologic_Event
            ))
            g.add((
                f,
                GSOC.isParticipantIn,
                ge
            ))
            gp = BNode()
            g.add((
                ge,
                GSOC.hasConstituent,
                gp
            ))
            g.add((
                gp,
                RDF.type,
                GSOG.Geologic_Process
            ))
            if self.eventProcess is not None:
                geologic_processes = {
                    # "": GSOG.Additive_Process,
                    # "": GSOG.Deformation,
                    # "": GSOG.Subtractive_Process,
                    # "": GSOG.Transformation,
                    EP.accretion: GSPR.Accretion,
                    EP.biological_precipitation: GSPR.Biological_Precipitation,
                    EP.biological_weathering: GSPR.Biological_Weathering,
                    EP.chemical_precipitation: GSPR.Chemical_Precipitation,
                    EP.chemical_weathering: GSPR.Chemical_Weathering,
                    EP.contact_metamorphism: GSPR.Contact_Metamorphism,
                    EP.continental_breakup: GSPR.Continental_Breakup,
                    EP.continental_collision: GSPR.Continental_Collision,
                    EP.debris_flow_deposition: GSPR.Debris_Flow_Deposition,
                    EP.deep_water_oxygen_depletion: GSPR.Deep_Water_Oxygen_Depletion,
                    EP.deformation_twinning: GSPR.Deformation_Twinning,
                    EP.deposition: GSPR.Deposition,
                    # "": GSPR.Deposition_Hiatus,
                    EP.diagenetic_process: GSPR.Diagenetic_Process,
                    EP.diffusion_creep: GSPR.Diffusion_Creep,
                    EP.dislocation_metamorphism: GSPR.Dislocation_Metamorphism,
                    EP.dissolution: GSPR.Dissolution,
                    EP.dissolution_creep: GSPR.Dissolution_Creep,
                    # "": GSPR.Ductile_Flattening,
                    EP.ductile_flow: GSPR.Ductile_Flow,
                    # "": GSPR.Ductile_Simple_Shear,
                    EP.effusive_eruption: GSPR.Effusive_Eruption,
                    EP.erosion: GSPR.Erosion,
                    EP.eruption: GSPR.Eruption,
                    EP.excavation: GSPR.Excavation,
                    EP.faulting: GSPR.Faulting,
                    # "": GSPR.Flexural_Slip,
                    EP.folding: GSPR.Folding,
                    EP.fracturing: GSPR.Fracturing,
                    EP.frost_shattering: GSPR.Frost_Shattering,
                    # "": GSPR.Geodynamo_Process,
                    EP.geomagnetic_process: GSPR.Geomagnetic_Process,
                    EP.grading: GSPR.Grading,
                    EP.haloclasty: GSPR.Haloclasty,
                    EP.hawaiian_eruption: GSPR.Hawaiian_Eruption,
                    EP.human_activity: GSPR.Human_Deposition,  # not exact
                    EP.hydration: GSPR.Hydration,
                    EP.hydrolysis: GSPR.Hydrolysis,
                    EP.ice_erosion: GSPR.Ice_Erosion,
                    EP.intrusion: GSPR.Intrusion_Process,  # not exact
                    # "": GSPR.Lava_Flow,
                    EP.magmatic_crystallisation: GSPR.Magmatic_Cystallisation,
                    EP.magmatic_process: GSPR.Magmatic_Process,
                    EP.mass_wasting: GSPR.Mass_Wasting,
                    EP.mass_wasting_deposition: GSPR.Mass_Wasting_Deposition,
                    EP.mechanical_deposition: GSPR.Mechanical_Deposition,
                    EP.melting: GSPR.Melting,
                    EP.metamorphic_process: GSPR.Metamorphic_Process,
                    # "": GSPR.Metasomatism,
                    EP.microfracturing: GSPR.Microfracturing,
                    # "": GSPR.Mountain_Building,
                    EP.obduction: GSPR.Obduction,
                    EP.organic_accumulation: GSPR.Organic_Accumulation,
                    EP.oxidation: GSPR.Oxidation,
                    EP.partial_melting: GSPR.Partial_Melting,
                    EP.physical_weathering: GSPR.Physical_Weathering,
                    EP.plinian_eruption: GSPR.Plinian_Eruption,
                    EP.polar_wander: GSPR.Polar_Wander,
                    EP.pressure_release_weathering: GSPR.Pressure_Release_Weathering,
                    EP.pyroclastic_eruption: GSPR.Pyroclastic_Eruption,
                    # "": GSPR.Pyrometamorphism,
                    # "": GSPR.Regional_Metamorphism,
                    EP.rifting: GSPR.Rifting,
                    EP.sea_level_change: GSPR.Sea_Level_Fluctuation,  # not exact
                    EP.sedimentary_process: GSPR.Sedimentary_Process,
                    EP.shearing: GSPR.Shearing,
                    EP.spreading: GSPR.Spreading,
                    EP.strombolian_eruption: GSPR.Strombolian_Eruption,
                    # "": GSPR.Subaerial_Extrusion,
                    # "": GSPR.Subaqueous_Extrusion,
                    EP.subduction: GSPR.Subduction,
                    EP.tectonic_process: GSPR.Tectonic_Process,
                    EP.thermal_shock_weathering: GSPR.Thermal_Shock_Weathering,
                    EP.traction_saltation_or_suspension_deposition: GSPR.Traction_Saltation_or_Suspension_Deposition,
                    EP.transform_faulting: GSPR.Transform_Faulting,
                    EP.turbidity_current_deposition: GSPR.Turbidity_Current_Deposition,
                    EP.vulcanian_eruption: GSPR.Vulcanian_Eruption,
                    EP.water_erosion: GSPR.Water_Erosion,
                    EP.weathering: GSPR.Weathering,
                    EP.wind_erosion: GSPR.Wind_Erosion,
                }
                gp_subtype = geologic_processes.get(URIRef(self.eventProcess[0]))
                if gp_subtype is not None:
                    g.add((
                        gp,
                        RDF.type,
                        gp_subtype
                    ))

            GSGF = Namespace("http://loop3d.org/GSO/ontology/2020/1/geologicfeature/")
            g.bind("gsgf", GSGF)

            if self.youngerNamedAge is not None \
                    or self.olderNamedAge is not None \
                    or self.youngerBound is not None \
                    or self.olderBound is not None:

                ti = BNode()
                g.add((
                    ge,
                    GSOC.directTemporalOccupies,
                    ti
                ))

                if self.youngerNamedAge is not None:
                    g.add((
                        ti,
                        GSOC.timeFinishedBy,
                        URIRef(self.youngerNamedAge[0])
                    ))

                if self.olderNamedAge is not None:
                    g.add((
                        ti,
                        GSOC.timeStartedBy,
                        URIRef(self.olderNamedAge[0])
                    ))

                if self.youngerBound is not None or self.olderBound is not None:

                    tr = BNode()
                    g.add((
                        ti,
                        GSOC.hasValue,
                        tr
                    ))

                    if self.youngerBound is not None:
                        yb = BNode()
                        g.add((
                            tr,
                            GSOC.hasEndValue,
                            yb
                        ))
                        g.add((
                            yb,
                            RDF.type,
                            GSOC.Time_Numeric_Value
                        ))
                        g.add((
                            yb,
                            RDF.type,
                            GSOC.Geologic_Time_Date
                        ))
                        g.add((
                            yb,
                            GSOG.hasDataValue,
                            Literal(self.youngerBound[0], datatype=XSD.float)
                        ))
                        uom = BNode()
                        g.add((
                            yb,
                            GSOC.hasUOM,
                            uom
                        ))
                        g.add((
                            uom,
                            RDF.type,
                            URIRef(
                                LUNIT.ma
                                if self.youngerBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                                else self.youngerBound[1]
                            )
                        ))

                    if self.olderBound is not None:
                        ob = BNode()
                        g.add((
                            tr,
                            GSOC.hasStartValue,
                            ob
                        ))
                        g.add((
                            ob,
                            RDF.type,
                            GSOC.Time_Numeric_Value
                        ))
                        g.add((
                            ob,
                            RDF.type,
                            GSOC.Geologic_Time_Date
                        ))
                        g.add((
                            ob,
                            GSOG.hasDataValue,
                            Literal(self.youngerBound[0], datatype=XSD.float)
                        ))
                        uom = BNode()
                        g.add((
                            ob,
                            GSOC.hasUOM,
                            uom
                        ))
                        g.add((
                            uom,
                            RDF.type,
                            URIRef(
                                LUNIT.ma
                                if self.youngerBound[1] == "http://pid.geoscience.gov.au/def/voc/ga/uom/Ma"
                                else self.youngerBound[1]
                            )
                        ))
        return g


class StratUnitRenderer(Renderer):
    def __init__(self, request, collection_id: str, item_id: str, other_links: List[Link] = None):
        self.feature_id = item_id
        super().__init__(
            request,
            LANDING_PAGE_URL + "/collections/" + collection_id + "/item/" + item_id,
            profiles={
                "geosp": profile_geosparql,
                "loop3d": profile_loop3d,
                "su": profile_su,
                "gsmlb": profile_gsmlb
            },
            default_profile_token="su"
        )

        if self.profile != "gsmlb":
            g = get_graph()
            # get the URI for the Collection using the ID
            collection_uri = None
            for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
                collection_uri = s

            if collection_uri is None:
                raise Exception("You have entered an unknown Collection ID")

            # get URIs for things with this ID  - IDs may not be unique across Collections
            for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(item_id)):
                # if this Feature is in this Collection, return it
                if (s, DCTERMS.isPartOf, collection_uri) in g:
                    self.feature = StratUnit(str(s))
            self.links = []
            if other_links is not None:
                self.links.extend(other_links)

            self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype"]

    def render(self):
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "gsmlb":
            return Response(
                get_strat_unit("GA.GeologicProvince." + self.feature_id.replace("SU", ""), return_original_xml=True),
                mimetype="application/xml",
                headers=self.headers
            )
        elif self.profile == "su":
            if self.mediatype == "text/html":
                return self._render_su_html()
            else:
                return self._render_rdf(self.feature.to_su_graph())
        elif self.profile == "loop3d":
            return self._render_rdf(self.feature.to_loop3d_graph())

    def _render_su_html(self):
        _template_context = {
            "links": self.links,
            "feature": self.feature,
        }

        return Response(
            render_template("strat_unit.html", **_template_context),
            headers=self.headers,
        )

    def _render_rdf(self, g):
        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype, headers=self.headers)
        elif self.mediatype in Renderer.RDF_MEDIA_TYPES:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype, headers=self.headers)
        else:
            return Response(
                "The Media Type you requested, '{}', cannot be serialized to".format(self.mediatype),
                status=400,
                mimetype="text/plain"
            )
