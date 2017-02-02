Ruination uses DataService() as a base to quickly define data crud data services via SQLAlchemy
that are exposed to a http services via a serializer.

These services support a set of base methods for creating, saving, updating and fetching records.

Implementation Hooks.
---------------------

DataServiceBase provides implementation hooks that allow for customizing the behavior of the crud
service.

def on_before_save(self, instance)

def on_after_save(self, instance)

def on_before_new_instance(self, **kwargs)

def on_new_instance(self, instance)


def on_before_create(self, **kwargs)

def on_after_create(self, instance)



Argument Pre-Processing.
------------------------
Create / New Instance:
Update Instance:
Delete Instance: