from setuptools import setup, find_packages
import os

version = '1.8.3rc1'

setup(
    name='org.bccvl.site',
    version=version,
    description="BCCVL Policy Product",
    # long_description=open("README.txt").read() + "\n" +
    #                  open(os.path.join("docs", "HISTORY.txt")).read(),
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
    ],
    keywords='',
    author='',
    author_email='',
    url='http://svn.plone.org/svn/collective/',
    license='GPL',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['org', 'org.bccvl'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',  # distribute
        'five.pt',
        'org.bccvl.theme',
        'Products.AutoUserMakerPASPlugin',
        'Products.ShibbolethPermissions',
        'sc.social.like',
        'gu.transmogrifier',
        'plone.api',
        'collective.js.jqueryui',
        'collective.js.uix.multiselect',
        'collective.geo.contentlocations',
        'collective.geo.geographer',
        'collective.geo.kml',
        'collective.geo.mapwidget',
        'collective.geo.openlayers',
        'collective.geo.settings',
        'collective.z3cform.mapwidget',
        'collective.googleanalytics',
        'collective.quickupload',
        'collective.onlogin',
        'collective.z3cform.widgets',
        #'collective.deletepermission', careful it interfers with delete buttons when not activated
        #'collective.z3cform.chosen',
        'plone.app.folderui',
        'borg.localrole',
        'plone.app.contenttypes',
        'decorator',
        'collective.setuphelpers',
        'plone.app.contentlisting',
        'collective.transmogrifier',
        'collective.jsonmigrator',
        'transmogrify.dexterity',
        'quintagroup.transmogrifier',
        'org.bccvl.compute',
        'org.bccvl.tasks',
        #'python-openid', # enable openid
        #'plone.app.openid',  # try to load configure stuff
        #'atreal.richfile.qualifier',
        #'atreal.richfile.image',
        #'atreal.richfile.preview',
        #'atreal.richfile.streaming',
        #'atreal.richfile.metadata',
        #'atreal.filestorage.common',
        #'atreal.filestorage.blobfile',
        #'atreal.filecart',
        #'atreal.layouts', # MatrixView
        # 'affinitic.zamqp',
        # 'pika == 0.5.2', -> rather us kombu
        # TODO: verify that we need this.
        #'plone.app.relationfield',
    ],
    extras_require={
        'test': ['plone.app.testing',
                 'unittest2'],
        'deprecated':  ['gu.repository.content',
                        'gu.plone.rdf',
                        'dexterity.membrane',
                        ],
        'experimental': ['eea.facetednavigation']
    },

    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone
    """,
    )
