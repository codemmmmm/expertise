the file classes/models.py is a copy of the models.py from the django project
with django_neomodel.DjangoNode replaced by neomodel.StructuredNode because
I didn't know how to import the django stuff properly

additionally, trying to create advisor relationships while exporting causes an error
that I believe is caused by the models.py defining the advisor relationship
with a string instead of a class as parameter (which cannot be changed).
this seems to cause a name conflict with the neomodel library which I was only able
to fix by renaming my classes.Person class to a different name. simply importing
both Person classes with different names didn't work.