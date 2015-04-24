from org.bccvl.site.interfaces import IDownloadInfo, IBCCVLMetadata
# had to remove this to avoid circular import because of form hints widgets in interfaces.py
#from org.bccvl.site.content.interfaces import IDataset
from plone.uuid.interfaces import IUUID
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.interfaces import ICatalogBrain
from plone.app.uuid.utils import uuidToObject


# TODO: brains=True would be more useful for internal API?
def query(context=None, brains=False, **kw):
    """Query catalog for datasets.

    Queries the catalog with context as path (or navigation root if None),
    and returns a generator with dataset specific metadat about each indexed
    dataset.

    brains ... if True, this method returns the catalog brains directly.
               if False additional metadata about each item is generated
    """
    if context is None:
        # FIXME: lookup site root from nothing
        raise NotImplementedError()
    # assume we have a context
    query = kw
    query.update({
        'object_provides': 'org.bccvl.site.content.interfaces.IDataset',
        #'object_provides': IDataset.__identifier__,
        'path': '/'.join(context.getPhysicalPath()),
    })

    # TODO: should optimise this. e.g. return generator,
    pc = getToolByName(context, 'portal_catalog')
    for brain in pc.searchResults(query):
        if brains:
            yield brain
        else:
            yield getdsmetadata(brain)


# TODO: turn this into some adapter lookup component-> maybe use
# z3c.form validation adapter lookup?
def find_projections(ctx, emission_scenarios, climate_models, years, resolution=None):
        """Find Projection datasets for given criteria"""
        pc = getToolByName(ctx, 'portal_catalog')
        result = []
        params = {
            'BCCEmissionScenario': emission_scenarios,
            'BCCGlobalClimateModel': climate_models,
            'BCCDataGenre': 'DataGenreFC'
        }
        if resolution:
            params['BCCResolution'] = resolution
        brains = pc.searchResults(**params)
        for brain in brains:
            md = IBCCVLMetadata(brain.getObject())
            year = md.get('temporal', None)
            if year in years:
                # TODO: yield?
                result.append(brain)
        return result


def getdsmetadata(ds):
    # TODO: support brain, obj and uuid string (URI as well?)
    # extract info about files
    if ICatalogBrain.providedBy(ds):
        ds = ds.getObject()
        # TODO: try to use brains only here
        #    url: ds.getURL()
        #    id: ds.UID,
        #    description: ds.Description
    # start with metadata annotation
    md = {
        #'@context': { },
        '@id': IUUID(ds),
        '@type':  ds.portal_type,
        'url': ds.absolute_url(),
        'id': IUUID(ds),
        'title': ds.title,
        'description': ds.description,
    }
    md.update(IBCCVLMetadata(ds))
    dlinfo = IDownloadInfo(ds)
    md.update({
        'mimetype': dlinfo['contenttype'],
        'filename': dlinfo['filename'],
        'file': dlinfo['url'],
        'vizurl': dlinfo['alturl'][0]
    })
    return md


# FIXME: this method is potentially very slow
def getThresholds(datasets, thresholds=None):
    # dataset to get thresholds for
    # thresholds a list of threshold names to return (if None return all)
    if not isinstance(datasets, list):
        datasets = [datasets]
    result = {}  # we have to return per experiment, per dataset/result
    for dataset in datasets:
        dataobj = uuidToObject(dataset)
        if dataobj is None:
            continue
        datamd = IBCCVLMetadata(dataobj)
        if datamd['genre'] == 'DataGenreFP':
            # we have a future projection ... go look for thresholds at SDM result
            sdmuuid = dataobj.__parent__.job_params['species_distribution_models']
            # get sdm result container
            sdmresult = uuidToObject(sdmuuid).__parent__
        elif datamd['genre'] == 'DataGenreCP':
            # we have a current projection ...
            sdmresult = dataobj.__parent__
        else:
            continue
        # We have the sdm result container ... find thresholds now
        pc = getToolByName(dataobj, 'portal_catalog')
        # find all model eval datasets
        thresholds = {}
        for evalbrain in pc.searchResults(path='/'.join(sdmresult.getPhysicalPath()),
                                          BCCDataGenre='DataGenreSDMEval'):
            evalmd = IBCCVLMetadata(evalbrain.getObject())
            # FIXME: ideally we got only datasets with thresholds back here, but
            #        at the moment DataGenreSDMEval is aso used for graphs (png  files)
            #        generated by the algorithms
            if 'thresholds' not in evalmd:
                continue
            # TODO: merging of thresholds is random here
            thresholds.update(evalmd['thresholds'])
        result[dataset] = thresholds
    return result
