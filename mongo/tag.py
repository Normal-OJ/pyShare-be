from . import engine
from .base import MongoBase

__all__ = ['Tag']


Class Tag(MongoBase, engine=engine.Tag):
	def __init__(self, value):
		self.value = value

	def delete(self):
		'''
        delete the problem
        '''
        # remove tag from problem if it have
        engine.Problem.objects(tags=self.value).update(pull__tags=self.value)
        self.obj.delete()

    def push_to_course():
    	'''
    	push tag into a course's tags
    	'''

    def pop_from_course():
    	'''
    	pop tag out from a course's tags
    	'''

	@classmethod
	def add(value):
		'''
		add a tag to db
		'''
		t = engine.Tag(value)
        t.save()
        