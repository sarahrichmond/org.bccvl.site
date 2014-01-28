from Products.Five import BrowserView
from plone.app.content.browser.interfaces import IFolderContentsView
from zope.interface import implementer
from plone.app.uuid.utils import uuidToObject
from org.bccvl.site.vocabularies import envirolayer_source
from org.bccvl.site.api import QueryAPI
from collections import defaultdict


def get_title_from_uuid(uuid):
    obj = uuidToObject(uuid)
    if obj:
        return obj.title
    return None


# FIXME: this view needs to exist for default browser layer as well
#        otherwise diazo.off won't find the page if set up.
#        -> how would unthemed markup look like?
#        -> theme would only have updated template.
@implementer(IFolderContentsView)
class DatasetsListingView(BrowserView):

    def datasets(self):
        api = QueryAPI(self.context)
        path = '/'.join(self.context.getPhysicalPath())
        return api.getDatasets(path={'query': path,
                                     'depth': -1})

    # def experiment_details(self, expbrain):
    #     details = {}

    #     if expbrain.portal_type == 'org.bccvl.content.projectionexperiment':
    #         details['type'] = 'PROJECTION'
    #     elif expbrain.portal_type == 'org.bccvl.content.sdmexperiment':
    #         # this is ripe for optimising so it doesn't run every time
    #         # experiments are listed
    #         envirolayer_vocab = envirolayer_source(self.context)
    #         environmental_layers = defaultdict(list)
    #         exp = expbrain.getObject()
    #         if exp.environmental_datasets:
    #             for dataset, layers in exp.environmental_datasets.items():
    #                 for layer in layers:
    #                     environmental_layers[dataset].append(
    #                         envirolayer_vocab.getTermByToken(str(layer)).title
    #                     )

    #         details.update({
    #             'type': 'SDM',
    #             'functions': ', '.join(
    #                 get_title_from_uuid(func) for func in exp.functions
    #             ),
    #             'species_occurrence': get_title_from_uuid(
    #                 exp.species_occurrence_dataset),
    #             'species_absence': get_title_from_uuid(
    #                 exp.species_absence_dataset),
    #             'environmental_layers': ', '.join(
    #                 '{}: {}'.format(get_title_from_uuid(dataset),
    #                                 ', '.join(layers))
    #                 for dataset, layers in environmental_layers.items()
    #             ),
    #         })
    #     return details
