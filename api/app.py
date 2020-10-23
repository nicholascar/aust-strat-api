import logging
from flask import (
    Flask,
    request,
    render_template,
    url_for,
    jsonify,
    Blueprint,
    Response
)
from flask_restx import Namespace, reqparse, Api, Resource
from api.config import *
from pyldapi import Renderer
from api.model import *
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

blueprint = Blueprint('api', __name__)


@app.route("/")
def landing_page():
    try:
        return LandingPageRenderer(request).render()
    except Exception as e:
        logging.debug(e)
        return Response(
            "The API cannot connect to its data source",
            status=500,
            mimetype="text/plain"
        )


api = Api(app, doc="/doc/", version='1.0', title="OGC LD API",
          description="Open API Documentation for this {}".format(API_TITLE))
# sapi = Namespace('oai', description="Search from DGGS Engine", version="1.0")
# api.add_namespace(sapi)
app.register_blueprint(blueprint)



@api.route("/spec")
class Spec(Resource):
    def get(self):
        return api.__schema__


@api.route("/conformance")
class ConformanceRoute(Resource):
    def get(self):
        q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcapi/>
            
            SELECT *
            WHERE {
                ?uri a ogcapi:ConformanceTarget ;
                   dcterms:title ?title
            }
            """
        graph = get_graph()
        conformance_classes = []
        for s in graph.subjects(predicate=RDF.type, object=OGCAPI.ConformanceTarget):
            uri = str(s)
            for o in graph.objects(subject=s, predicate=DCTERMS.title):
                title = str(o)
            conformance_classes.append((uri, title))
        return ConformanceRenderer(request, conformance_classes).render()


@api.route("/collections")
class CollectionsRoute(Resource):
    def get(self):
        return CollectionsRenderer(request).render()


@api.route("/collections/<string:collection_id>")
@api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
class CollectionRoute(Resource):
    def get(self, collection_id):
        g = get_graph()
        # get the URI for the Collection using the ID
        collection_uri = None
        for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
            collection_uri = s

        if collection_uri is None:
            return Response(
                "You have entered an unknown Collection ID",
                status=400,
                mimetype="text/plain"
            )

        return CollectionRenderer(request, collection_uri).render()


@api.route("/collections/<string:collection_id>/items")
@api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
class FeaturesRoute(Resource):
    def get(self, collection_id):
        return FeaturesRenderer(request, collection_id).render()


@api.route("/collections/<string:collection_id>/items/<string:item_id>")
@api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
@api.param("item_id", "The ID of a Feature in this Collection's list of Items")
class FeatureRoute(Resource):
    def get(self, collection_id, item_id):
        g = get_graph()
        # get the URI for the Collection using the ID
        collection_uri = None
        for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
            collection_uri = s

        if collection_uri is None:
            return Response(
                "You have entered an unknown Collection ID",
                status=400,
                mimetype="text/plain"
            )

        # get URIs for things with this ID  - IDs may not be unique across Collections
        for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(item_id)):
            # if this Feature is in this Collection, return it
            if (s, DCTERMS.isPartOf, collection_uri) in g:
                return ProvincesRenderer(request, str(s)).render()

        return Response(
            "The Feature you have entered the ID for is not part of the Collection you entered the ID for",
            status=400,
            mimetype="text/plain"
        )


@api.route("/object")
class ObjectRoute(Resource):
    def get(self):
        return "nothing"


def render_api_error(title, status, message, mediatype="text/html"):
    if mediatype == "application/json":
        return jsonify({
            "title": title,
            "status": status,
            "message": message
        }), status
    elif mediatype in Renderer.RDF_MEDIA_TYPES:
        pass
    else:  # mediatype == "text/html":
        return render_template(
            "error.html",
            title=title,
            status=status,
            message=message
        ), status


if __name__ == "__main__":
    logging.basicConfig(
        filename=LOGFILE,
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s",
    )

    app.run(debug=DEBUG, threaded=True, port=PORT)
