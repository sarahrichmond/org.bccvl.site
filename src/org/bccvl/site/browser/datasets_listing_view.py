from itertools import chain
from Products.Five import BrowserView
from plone.app.content.browser.interfaces import IFolderContentsView
from zope.interface import implementer
from plone.app.uuid.utils import uuidToObject
from org.bccvl.site.content.interfaces import IDataset
from org.bccvl.site.interfaces import IDownloadInfo, IJobTracker
from org.bccvl.site.browser.interfaces import IDatasetTools
from org.bccvl.site.api.dataset import getdsmetadata
from Products.CMFCore.utils import getToolByName
from zope.security import checkPermission
from zope.component import getMultiAdapter, getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
import Missing


def get_title_from_uuid(uuid):
    obj = uuidToObject(uuid)
    if obj:
        return obj.title
    return None


@implementer(IDatasetTools)
class DatasetTools(BrowserView):
    """A helper view to deal with datasets.

    It provides a couple of methods that are helpful within a page template.
    """

    def get_transition(self, itemob=None):
        #return checkPermission('cmf.RequestReview', self.context)
        if itemob is None:
            itemob = self.context
        wftool = getToolByName(itemob, 'portal_workflow')
        wfid = wftool.getChainFor(itemob)[0]
        wf = wftool.getWorkflowById(wfid)
        # TODO: use workflow_tool.getTransitionsFor
        # check whether user can invoke transition
        # TODO: expects simple publication workflow publish/retract
        for transition in ('publish', 'retract'):
            if wf.isActionSupported(itemob, transition):
                return transition
        return {}

    def get_download_info(self, item=None):
        if item is None:
            item = self.context
        return IDownloadInfo(item)

    def can_modify(self, itemob=None):
        if itemob is None:
            itemob = self.context
        return checkPermission('cmf.ModifyPortalContent', itemob)

    # TODO: maybe move to different tools view? (not dataset specific)
    def local_roles_action(self, itemobj=None):
        if itemobj is None:
            itemobj = self.context
        context_state = getMultiAdapter((itemobj, self.request),
                                        name=u'plone_context_state')
        for action in context_state.actions().get('object'):
            if action.get('id') == 'local_roles':
                return action
        return {}

    def metadata(self, itemobj=None):
        if itemobj is None:
            itemobj = self.context
        return getdsmetadata(itemobj)

    def job_state(self, itemobj=None):
        if itemobj is None:
            itemobj = self.context
        # FIXME: assume we have a IContentListingObject
        return itemobj._brain.job_state


# FIXME: this view needs to exist for default browser layer as well
#        otherwise diazo.off won't find the page if set up.
#        -> how would unthemed markup look like?
#        -> theme would only have updated template.
@implementer(IFolderContentsView)
class DatasetsListingView(BrowserView):

    def contentFilter(self):
        portal_state = getMultiAdapter(
            (self.context, self.request), name="plone_portal_state")
        member = portal_state.member()

        query = {}

        text = self.request.get('datasets.filter.text')
        if text:
            query['SearchableText'] = text

        genre = self.request.get('datasets.filter.genre')
        if genre:
            query['BCCDataGenre'] = [self.genre_vocab.by_token[token].value for token in genre]
        else:
            # if nothing selcted use all values in vocab
            query['BCCDataGenre'] =  list(self.genre_vocab.by_value.keys())

        resolution = self.request.get('datasets.filter.resolution')
        if resolution:
            query['BCCResolution'] = [self.resolution_vocab.by_token[token].value for token in resolution]

        # FIXME: source filter is incomplete
        source = self.request.get('datasets.filter.source')
        if source:
            query['Creator'] = []
            for token in source:
                if token == 'user':
                    query['Creator'].append(member.getId())
                elif token == 'admin':
                    query['Creator'].append(token)
                # FIXME: missing: shared, ala

        # add fixed query parameters:
        query .update({
            'path': {
                # 'query': portal_state.navigation_root_path(),
                'query': '/'.join(self.context.getPhysicalPath()),
                'depth': -1
            },
            'sort_on': 'modified',
            'sort_order': 'descending',
            'object_provides': IDataset.__identifier__,
        })
        return query

    def datasetslisting(self):
        """
        Render the datasets listing section.

        Accepted parameters:
        - Batch range
        - filters
        - ajax ... render only list
        - uuid + ajax ... render only one entry
        """
        query_params = self.contentFilter()
        b_size = int(self.request.get('b_size', 20))
        b_start = int(self.request.get('b_start', 0))

        pc = getToolByName(self.context, 'portal_catalog')
        from Products.CMFPlone import Batch
        brains = pc.queryCatalog(query_params)  # show_all=1?? show_inactive=show_inactive?
        batch = Batch(brains, b_size, b_start, orphan=0)
        return batch

    def __call__(self):
        # initialise instance variables, we'll do it here so that we have
        # security set up and have to do it only once per request
        self.genre_vocab = SimpleVocabulary(tuple(chain.from_iterable((
            getUtility(IVocabularyFactory, 'org.bccvl.site.SpeciesDataGenreVocabulary')(self.context),
            getUtility(IVocabularyFactory, 'org.bccvl.site.EnvironmentalDataGenreVocabulary')(self.context)
        ))))
        self.resolution_vocab = getUtility(IVocabularyFactory,  'org.bccvl.site.ResolutionVocabulary')(self.context)
        self.source_vocab = SimpleVocabulary((
            SimpleTerm('user', 'user', u'My Datasets'),
            SimpleTerm('admin', 'admin', u'Provided by BCCVL'),
            SimpleTerm('ala', 'ala', u'Imported from ALA'),
            SimpleTerm('shared', 'shared', 'Shared'),
        ))
        import ipdb; ipdb.set_trace()
        return super(DatasetsListingView, self).__call__()

    # Various datasets listing helpers
    def genre_list(self):
        selected = self.request.get('datasets.filter.genre', ())
        for genre in self.genre_vocab:
            yield {
                'selected': genre.token in selected,
                'disabled': False,
                'token': genre.token,
                'label': genre.title
            }

    def resolution_list(self):
        selected = self.request.get('datasets.filter.resolution', ())
        for genre in self.resolution_vocab:
            yield {
                'selected': genre.token in selected,
                'disabled': False,
                'token': genre.token,
                'label': genre.title
            }

    def source_list(self):
        selected = self.request.get('datasets.filter.source', ())
        for genre in self.source_vocab:
            yield {
                'selected': genre.token in selected,
                'disabled': False,
                'token': genre.token,
                'label': genre.title
            }

    def item_genre_title(self, genre):
        try:
            return self.genre_vocab.by_value[genre[0]].title
        except Missing.Value:
            return u'Missing Genre'
        except TypeError:
            return u'Invalid Genre {0}'.format(repr(genre))
        except KeyError:
            return u'Genre not found {0}'.format(genre)
        except IndexError:
            return u'Invalid Genre {0}'.format(repr(genre))
