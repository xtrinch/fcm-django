Using custom FCMDevice model
============================

If there's a need to store additional information or change type of fields in the FCMDevice model.
You could simple override this model. To do this, inherit your model from the AbstractFCMDevice class.

In your ``your_app/models.py``:

.. code-block:: python

    import uuid
    from django.db import models
    from fcm_django.models import AbstractFCMDevice


    class CustomDevice(AbstractFCMDevice):
        # fields could be overwritten
        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        # could be added new fields
        updated_at = models.DateTimeField(auto_now=True)

In your ``settings.py``:

.. code-block:: python

    FCM_DJANGO_FCMDEVICE_MODEL = "your_app.CustomDevice"


Keep ``fcm_django`` in ``INSTALLED_APPS`` so the package migrations continue to run.
That is especially important for any additional tables owned by this package, such as topic tracking.

In the DB there will be two tables: the historical default table created by this package and your custom table.
New device data will be written only to your custom table.

.. code-block:: python

    INSTALLED_APPS = (
        ...
        "fcm_django",
        "your_app", # your app should appears
        ...
    )

After setup your own ``Model`` don't forget to create ``migrations`` for your app and call ``migrate`` command.


If you choose to move forward with swapped models then:

1. On existed project you have to keep in mind there are required manual work to move data from one table to anther.
2. If there's any tables with FK to swapped model then you have to deal with them on your own.

Note: This functionality based on `Swapper <https://pypi.org/project/swapper/>`_ that based on functionality
that allow to use a `custom User model <https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#substituting-a-custom-user-model>`_.
So this functionality have the same limitations.
The most is important limitation it is that is difficult to start out with a default (non-swapped) model
and then later to switch to a swapped implementation without doing some migration hacking.
