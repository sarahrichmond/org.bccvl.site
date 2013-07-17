from org.bccvl.site import defaults
from org.bccvl.site.namespace import BCCVOCAB
from gu.repository.content.interfaces import IRepositoryItem

class QueryAPI(object):
    """
    Provides API for common queries 
    """
    def __init__(self, context):
        site = context.portal_url.getPortalObject()

        self.context = context
        self.site = site
        self.site_physical_path = '/'.join(site.getPhysicalPath())
        self.portal_catalog = site.portal_catalog
        
    def getDatasets(self, genre):
        datasets_physical_path = '/'.join(
            [self.site_physical_path, defaults.DATASETS_FOLDER_ID]
        )
        brains = self.portal_catalog(
            path = {'query': datasets_physical_path},
            BCCDataGenre = genre,
        )
        return brains

    def getSpeciesOccurrenceDatasets(self):
        return self.getDatasets(BCCVOCAB['DataGenreSO'])
    
    def getSpeciesDistributionDatasets(self):
        return self.getDatasets(BCCVOCAB['DataGenreSD'])

    def getEnvironmentalDatasets(self):
        return self.getDatasets(BCCVOCAB['DataGenreE'])

    def getFutureClimateDatasets(self):
        return self.getDatasets(BCCVOCAB['DataGenreFC'])

    def getFunctions(self):
        functions_physical_path = '/'.join(
            [self.site_physical_path, defaults.FUNCTIONS_FOLDER_ID]
        )
        brains = self.portal_catalog(
            path = {'query': functions_physical_path},
            object_provides = IRepositoryItem.__identifier__
        )
        return brains
