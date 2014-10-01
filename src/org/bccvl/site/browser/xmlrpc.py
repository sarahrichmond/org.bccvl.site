from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
#from zope.publisher.browser import BrowserView as Z3BrowserView
#from zope.publisher.browser import BrowserPage as Z3BrowserPage  # + publishTraverse
#from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound
#from functools import wraps
from decorator import decorator
from plone.app.uuid.utils import uuidToObject, uuidToCatalogBrain
from org.bccvl.site.interfaces import IJobTracker
from org.bccvl.site.content.interfaces import IProjectionExperiment
from org.bccvl.site.content.interfaces import ISDMExperiment
from org.bccvl.site.content.interfaces import IBiodiverseExperiment
from org.bccvl.site.content.dataset import IDataset
from org.bccvl.site import defaults
from org.bccvl.site.namespace import BCCPROP, BCCVOCAB, DWC, BIOCLIM, NFO
from ordf.namespace import DC
import logging
from gu.z3cform.rdf.interfaces import IORDF, IGraph, IResource
from zope.component import getUtility, queryUtility
from zope.schema.vocabulary import getVocabularyRegistry
from zope.schema.interfaces import IContextSourceBinder
import json
from Products.statusmessages.interfaces import IStatusMessage
from org.bccvl.site.browser.ws import IDataMover, IALAService
from plone.dexterity.utils import createContentInContainer
from rdflib.resource import Resource
from rdflib import Literal, URIRef
from gu.z3cform.rdf.utils import Period
from decimal import Decimal
from org.bccvl.site.api.dataset import getdsmetadata
from org.bccvl.site.api import dataset


LOG = logging.getLogger(__name__)


def decimal_encoder(o):
    """ converts Decimal to something the json module can serialize.
    Usually with python 2.7 float rounding this creates nice representations
    of numbers, but there might be cases where rounding may cause problems.
    E.g. if precision required is higher than default float rounding.
    """
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(repr(o) + " is not JSON serializable")


# self passed in as *args
@decorator  # well behaved decorator that preserves signature so that
            # apply can inspect it
def returnwrapper(f, *args, **kw):
    # see http://code.google.com/p/mimeparse/
    # self.request.get['HTTP_ACCEPT']
    # self.request.get['CONTENT_TYPE']
    # self.request.get['method'']
    # ... decide on what type of call it is ... json?(POST),
    #     xmlrpc?(POST), url-call? (GET)

    # in case of post extract parameters and pass in?
    # jsonrpc:
    #    content-type: application/json-rpc (or application/json,
    #    application/jsonrequest) accept: application/json-rpc (or
    #    --""--)

    isxmlrpc = False
    view = args[0]
    if view.request['CONTENT_TYPE'] == 'text/xml':
        # we have xmlrpc
        isxmlrpc = True

    ret = f(*args, **kw)
    # return ACCEPT encoding here or IStreamIterator, that encodes
    # stuff on the fly could handle response encoding via
    # request.setBody ... would need to replace response instance of
    # request.response. (see ZPublisher.xmlprc.response, which wraps a
    # default Response)
    # FIXME: this is a bad workaround for
    #        we call these wrapped functions internally, from templates and
    #        as ajax calls and xmlrpc calls, and expect different return encoding.
    #        ajax: json
    #        xmlrpc: xml, done by publisher
    #        everything else: python
    if not view.request['URL'].endswith(f.__name__):
        # not called directly, so return ret as is
        return ret

    # if we don't have xmlrpc we serialise to json
    if not isxmlrpc:
        ret = json.dumps(ret, default=decimal_encoder)
        view.request.response['CONTENT-TYPE'] = 'application/json'
    return ret


class DataSetManager(BrowserView):
    # DS Manager API on Site Root

    @returnwrapper
    # TODO: this method can be removed and use query(UID='') instead
    def metadata(self, datasetid):
        query = {'UID': datasetid}
        ds = dataset.query(self.context, **query)
        if ds:
            # we have a generator, let's pick the first result
            # metadata is extracted by query
            ds = next(ds, None)
        if ds is None:
            raise NotFound(self.context,  datasetid,  self.request)
        return ds

    # TODO: backwards compatible name
    @returnwrapper
    def getMetadata(self, datasetid):
        return self.metadata(datasetid)

    @returnwrapper
    def getRAT(self, datasetid, layer=None):
        query = {'UID': datasetid}
        if layer:
            layer=URIRef(layer)
        dsbrain = dataset.query(self.context, brains=True, **query)
        if dsbrain:
            dsbrain = next(dsbrain, None)
        if not dsbrain:
            raise NotFound(self.context, datasetid, self.request)
        res = IResource(dsbrain)
        rat = res.value(BCCPROP['rat'])
        if not rat:
            # nothing on dataset itself, maybe there are archive items?
            for ai in res.objects(BCCPROP['hasArchiveItem']):
                alayer = ai.value(BIOCLIM['bioclimVariable'])
                if alayer and alayer.identifier == layer:
                    rat = ai.value(BCCPROP['rat'])
        # if we have a rat, let's try and parse it
        if rat:
            try:
                rat = json.loads(unicode(rat))
            except Exception as e:
                LOG.warning("Couldn't decode Raster Attribute Table from metadata. %s: %s", self.context, repr(e))
                rat = None
        return rat


    @returnwrapper
    def query(self):
        # TODO: remove some parameters from request?
        #       e.g only matching with catalog indices
        #           only certain indices
        #       remove batching and internal parameters like brains
        query = self.request.form
        # TODO: should optimise this. e.g. return generator,
        objs = []
        for item in dataset.query(self.context, **query):
            objs.append(item)
        return objs

    @returnwrapper
    # TODO: need a replacement for this. it's a convenience function for UI
    def queryDataset(self, genre=None, layers=None):
        params = {'object_provides': IDataset.__identifier__}
        if genre:
            if not isinstance(genre, (tuple, list)):
                genre = (genre, )
            params['BCCDataGenre'] = {'query': [URIRef(g) for g in genre],
                                      'operator': 'or'}
        if layers:
            if not isinstance(layers, (tuple, list)):
                layers = (layers, )
            params['BCCEnviroLayer'] = {'query': [URIRef(l) for l in layers],
                                        'operator': 'and'}
        result = []
        for brain in dataset.query(self.context, True, **params):
            result.append({'uuid': brain.UID,
                           'title': brain.Title})
        return result

    # TODO: specific for one view (add projection)
    @returnwrapper
    def getFutureClimateDatasets(self):
        # TODO: should move this to Projection Add Form and let form
        # do the parameter parsing
        # reads:
        #   form.widgets.years  W3CDTF
        #   form.widgets.emission_scenarios URIRefs
        #   form.widgets.climate_models URIRefs
        # 1. read request:
        years = self.request.get('form.widgets.years')
        emsc = self.request.get('form.widgets.emission_scenarios')
        gcms = self.request.get('form.widgets.climate_models')
        # 2. no search if we have no values
        if not all((years, emsc, gcms)):
            return 0
        # 3. make sure we have lists
        years = [years] if not isinstance(years, list) else years
        emsc = [emsc] if not isinstance(emsc, list) else emsc
        gcms = [gcms] if not isinstance(gcms, list) else gcms
        # 4. convert to proper values
        years = [Literal(x, datatype=DC['Period']) for x in years]
        emsc = [URIRef(x) for x in emsc]
        gcms = [URIRef(x) for x in gcms]
        # 5. search
        res = dataset.find_projections(self.context, emsc, gcms, years)
        return len(res)

    # TODO: this is rather experiment API
    @returnwrapper
    def getSDMDatasets(self):
        # get all SDM current projection datasets
        pc = getToolByName(self.context, 'portal_catalog')
        sdmbrains = pc.searchResults(
            object_provides=ISDMExperiment.__identifier__,
            sort_on='sortable_title')  # date?
        sdms = []
        for sdmbrain in sdmbrains:
            # TODO: this loop over loop is inefficient
            # TODO: this pattern is all the same across, get XXXDatasets
            datasets = []
            for dsbrain in pc.searchResults(
                    path=sdmbrain.getPath(),
                    BCCDataGenre=BCCVOCAB['DataGenreCP']):
                # get required metadata about dataset
                datasets.append({
                    #"files": [raster file names],
                    "title": dsbrain.Title,
                    "uuid": dsbrain.UID,
                    "url": dsbrain.getURL(),
                    #"year", "gcm", "msc", "species"
                })
            sdms.append({
                #"species": [],
                #"years": [],
                "name": sdmbrain.Title,
                "uuid": sdmbrain.UID,
                "url": sdmbrain.getURL(),
                "result": datasets
            })
        return {'sdms': sdms}

    # TODO: this is rather experiment API
    @returnwrapper
    def getBiodiverseDatasets(self):
        # TODO: there must be a way to do this with lfewer queries
        pc = getToolByName(self.context, 'portal_catalog')
        biodiversebrains = pc.searchResults(
            object_provides=IBiodiverseExperiment.__identifier__,
            sort_on='sortable_title')  # date?
        biodiverses = []
        for biodiversebrain in biodiversebrains:
            # search for datasets with this experiment
            datasets = []
            # TODO: query for data genre class?
            for dsbrain in pc.searchResults(
                    path=biodiversebrain.getPath(),
                    BCCDataGenre=(BCCVOCAB['DataGenreENDW_CWE'],
                                  BCCVOCAB['DataGenreENDW_WE'],
                                  BCCVOCAB['DataGenreENDW_RICHNESS'],
                                  BCCVOCAB['DataGenreENDW_SINGLE'],
                                  BCCVOCAB['DataGenreREDUNDANCY_SET1'],
                                  BCCVOCAB['DataGenreREDUNDANCY_SET2'],
                                  BCCVOCAB['DataGenreREDUNDANCY_ALL'])):
                # get required metadata about dataset
                datasets.append({
                    "title": dsbrain.Title,
                    "uuid": dsbrain.UID,
                    "url": dsbrain.getURL(),
                })
            biodiverses.append({
                "name": biodiversebrain.Title,
                "uuid": biodiversebrain.UID,
                "url": biodiversebrain.getURL(),
                "result": datasets
            })
        return {'biodiverses': biodiverses}

    # TODO: This method is very specific to UI in use,...
    #       maybe move to UI specific part?
    @returnwrapper
    def getProjectionDatasets(self):
        pc = getToolByName(self.context, 'portal_catalog')
        # to make it easire to produce required structure do separate queries
        # 1st query for all projection experiments
        projbrains = pc.searchResults(
            object_provides=IProjectionExperiment.__identifier__,
            sort_on='sortable_title')  # date?
        # the list to collect results
        projections = []
        for projbrain in projbrains:
            # get all result datasets from experiment and build list
            datasets = []
            agg_species = set()
            agg_years = set()
            for dsbrain in pc.searchResults(
                    path=projbrain.getPath(),
                    BCCDataGenre=BCCVOCAB['DataGenreFP']):
                # get year, gcm, emsc, species, filename/title, fileuuid
                # TODO: Result is one file per species ... should this be a dict by species or year as well?
                # FIXME: build on dataset, check if a sparql query using all dsbrains at once would be faster?
                ds = dsbrain.getObject()
                dsgraph = IGraph(ds)
                # parse year
                period = dsgraph.value(dsgraph.identifier, DC['temporal'])
                year = Period(period).start if period else None
                gcm = dsgraph.value(dsgraph.identifier, BCCPROP['gcm'])
                gcm = unicode(gcm) if gcm else None
                emsc = dsgraph.value(dsgraph.identifier, BCCPROP['emissionscenario'])
                emsc = unicode(emsc) if emsc else None
                species = dsgraph.value(dsgraph.identifier, DWC['scientificName'])
                species = unicode(species) if species else None
                resolution = unicode(dsbrain.BCCResolution)
                dsinfo = {
                    # passible fields on brain:
                    #   Description, BCCResolution
                    #   ds.file.contentType
                    # TODO: restructure ... tile, filename no list
                    "title":  dsbrain.Title,
                    "uuid": dsbrain.UID,
                    "files": [ds.file.filename],  # filenames
                    "year":  year,  # int or string?
                    "gcm":  gcm,  # URI? title? both?-> ui can fetch vocab to get titles
                    "emsc": emsc,  # URI
                    "species": species,   # species for this file ...
                    "resolution": resolution
                }
                # add info about sdm
                sdmuuid = ds.__parent__.job_params['species_distribution_models']
                sdm = uuidToCatalogBrain(sdmuuid).getObject()
                sdmresult = sdm.__parent__
                sdmexp = sdmresult.__parent__
                dsinfo['sdm'] = {
                    'title': sdmexp.title,
                    'algorithm': sdmresult.job_params['function'],
                    'url': sdm.absolute_url()
                }
                datasets.append(dsinfo)
                agg_species.add(species)
                agg_years.add(year)
            # TODO: could also aggregate all data on projections result:
            #       e.g. list all years, grms, emsc, aggregated from datasets
            projections.append({
                "name": projbrain.Title,  # TODO: rename to title
                "uuid":  projbrain.UID,   # TODO: rename to uuid
                "species":  tuple(agg_species),
                "years": tuple(agg_years),
                "result": datasets
            })
        # wrap in projections neccesarry?
        return {'projections': projections}

    # TODO: this is generic api ....
    @returnwrapper
    def getVocabulary(self, name):
        # TODO: check if there are vocabularies that need to be protected
        vocab = ()
        try:
            # TODO: getUtility(IVocabularyFactory???)
            vr = getVocabularyRegistry()
            vocab = vr.get(self.context, name)
        except:
            # eat all exceptions
            pass
        if not vocab:
            # try IContextSourceBinder
            vocab = queryUtility(IContextSourceBinder, name=name)
            if vocab is None:
                return []
            vocab = vocab(self.context)
        result = []
        for term in vocab:
            result.append({'token': term.token,
                           'title': term.title})
        return result

    @returnwrapper
    def getThresholds(self, datasets, thresholds=None):
        # datasets: a future projection dataset as a result of projectien experiment
        # thresholds: list of names to retrieve or all

        # FIXME FIXME: don't know which thresholds to pull from here
        #       store on resultc when importing/creating?
        #       store link to sdm on result?
        #       -> maybe store all necessary info to create an experiment from result?
        #       ->
        if not isinstance(datasets, list):
            datasets = [datasets]
        result = {}  # we have to return per experiment, per dataset/result
        for dataset in datasets:
            # 1. try to find sdm for projection
            projobj = uuidToObject(dataset)
            if projobj is None:
                continue
            # 2. thresholds can be found on result containers
            #      and associated sdm
            expinf = getattr(projobj.__parent__, 'experiment_infos', None)
            if not expinf:
                continue
            ths = expinf.get('sdm', {}).get('thresholds', None)
            if not ths:
                continue

            # ok we have thresholds, let's find the dataset uuid for this result
            pc = getToolByName(self.context, 'portal_catalog')
            if dataset not in result:
                result[dataset] = {}
            result[dataset].update(ths)
        # FIXME: just broke usage of old experiments in biodiverse experiments
        #        migrate? don't care? support both here?
        return result


class DataSetAPI(BrowserView):
    # DS Manager API on Dataset

    @returnwrapper
    def getMetadata(self):
        return getdsmetadata(self.context)

    @returnwrapper
    def share(self):
        # TODO: status message and redirect are not useful for ajax
        msg = u"Status changed"
        msg_type = 'info'
        try:
            wtool = getToolByName(self.context, 'portal_workflow')
            wtool.doActionFor(self.context,  'publish')
        except WorkflowException as e:
            msg = u"Status change failed"
            msg_type = 'error'
        IStatusMessage(self.request).add(msg, type=msg_type)
        next = self.request['HTTP_REFERER']
        if not next or next == self.request['URL']:
            next = self.context.absolute_url()
        self.request.response.redirect(next)

    @returnwrapper
    def unshare(self):
        # TODO: status message and redirect are not useful for ajax
        msg = u"Status changed"
        msg_type = 'info'
        try:
            wtool = getToolByName(self.context, 'portal_workflow')
            wtool.doActionFor(self.context,  'retract')
        except WorkflowException as e:
            msg = u"Status change failed"
            msg_type = 'error'
        IStatusMessage(self.request).add(msg, type=msg_type)
        next = self.request['HTTP_REFERER']
        if not next or next == self.request['URL']:
            next = self.context.absolute_url()
        self.request.response.redirect(next)


class JobManager(BrowserView):
    # job manager on Site Root

    @returnwrapper
    def getJobs(self):
        return ['job1', 'job2']

    @returnwrapper
    def getJobStatus(self,  jobid):
        return {'status': 'running'}


class JobManagerAPI(BrowserView):
    # job manager on experiment

    @returnwrapper
    def getJobStatus(self):
        return IJobTracker(self.context).state

    @returnwrapper
    def getJobStates(self):
        return IJobTracker(self.context).states


class ExperimentManager(BrowserView):

    @returnwrapper
    def getExperiments(self, id):
        return {'data': 'experimentmetadata+datasetids+jobid'}


from ZPublisher.Iterators import IStreamIterator
from zope.interface import implementer


@implementer(IStreamIterator)
class UrlLibResponseIterator(object):

    def __init__(self, resp):
        self.resp = resp
        try:
            self.length = int(resp.headers.getheader('Content-Length'))
        except:
            self.length = 0

    def __iter__(self):
        return self

    def next(self):
        data = self.resp.next()
        if not data:
            raise StopIteration
        return data

    def __len__(self):
        return self.length


class ALAProxy(BrowserView):

    #@returnwrapper ... returning file here ... returnwrapper not handling it properly
    def autojson(self, q, geoOnly=None, idxType=None, limit=None,
                 callback=None):
        # TODO: do parameter checking and maybe set defaults so that
        # js side doesn't have to do it
        ala = getUtility(IALAService)
        return self._doResponse(ala.autojson(q, geoOnly, idxType, limit,
                                             callback))

    #@returnwrapper ... returning file here ... returnwrapper not handling it properly
    def searchjson(self, q, fq=None, start=None, pageSize=None,
                   sort=None, dir=None, callback=None):
        # TODO: do parameter checking and maybe set defaults so that
        #       js side doesn't have to do it
        ala = getUtility(IALAService)
        return self._doResponse(ala.searchjson(q, fq, start, pageSize,
                                               sort, dir, callback))

    def _doResponse(self, resp):
        # TODO: add headers like:
        #    User-Agent
        #    orig-request
        #    etc...
        # TODO: check response code?
        for name in ('Date', 'Pragma', 'Expires', 'Content-Type',
                     'Cache-Control', 'Content-Language', 'Content-Length',
                     'transfer-encoding'):
            value = resp.headers.getheader(name)
            if value:
                self.request.response.setHeader(name, value)
        self.request.response.setStatus(resp.code)
        ret = UrlLibResponseIterator(resp)
        if len(ret) != 0:
            # we have a content-length so let the publisher stream it
            return ret
        # we don't have content-length and stupid publisher want's one
        # for stream, so let's stream it ourselves.
        while True:
            try:
                data = ret.next()
                self.request.response.write(data)
            except StopIteration:
                break


class DataMover(BrowserView):

    # TODO: typo in view ergistartion in api.zcml-> update js as well
    @returnwrapper
    def pullOccurrenceFromALA(self, lsid, taxon,  common=None):
        # TODO: check permisions?
        # 1. create new dataset with taxon, lsid and common name set
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        dscontainer = portal[defaults.DATASETS_FOLDER_ID][defaults.DATASETS_SPECIES_FOLDER_ID]

        title = [taxon]
        if common:
            title.append(u"({})".format(common))
        # TODO: check whether title will be updated in transmog import?
        #       set title now to "Whatever (import pending)"?
        # TODO: make sure we get a better content id that dataset-x
        ds = createContentInContainer(dscontainer,
                                      'org.bccvl.content.dataset',
                                      title=u' '.join(title))
        # TODO: add number of occurences to description
        ds.description = u' '.join(title) + u' imported from ALA'
        md = IGraph(ds)
        md = Resource(md, md.identifier)
        # TODO: provenance ... import url?
        # FIXME: verify input parameters before adding to graph
        md.add(BCCPROP['datagenre'], BCCVOCAB['DataGenreSpeciesOccurrence'])
        md.add(DWC['scientificName'], Literal(taxon))
        md.add(DWC['taxonID'], Literal(lsid))
        if common:
            md.add(DWC['vernacularName'], Literal(common))

        getUtility(IORDF).getHandler().put(md.graph)

        IStatusMessage(self.request).add('New Dataset created',
                                         type='info')

        # 2. create and push alaimport job for dataset
        # TODO: make this named adapter
        jt = IJobTracker(ds)
        status, message = jt.start_job()
        # Job submission state notifier
        IStatusMessage(self.request).add(message, type=status)

        return (status, message)

    @returnwrapper
    def checkALAJobStatus(self, job_id):
        # TODO: check permissions? or maybe git rid of this here and
        #       use job tracking for status. (needs job annotations)
        dm = getUtility(IDataMover)
        return dm.check_move_status(job_id)
