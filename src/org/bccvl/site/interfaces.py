from zope.interface import Interface

class IJobTracker(Interface):

    def start_job():
        """
        start this job
        """

    def get_job():
        """
        return the job instance
        """
