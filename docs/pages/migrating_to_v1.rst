Migration to v1.0
=================

We've replaced Python package ``pyfcm`` for Firebase's own package ``firebase-admin``.
Thus, we no longer use an API key. Instead, you'll need an environment variable
``GOOGLE_APPLICATION_CREDENTIALS`` which is a path pointing to your JSON-file stored
credentials. To learn more or view other options to input credentials, visit the
`Google Cloud docs <https://cloud.google.com/docs/authentication/getting-started>`_.

Finally, in your ``settings.py`` (or whatever imported file), add:

.. code-block:: python

    from firebase_admin import initialize_app
    FIREBASE_APP = initialize_app()
    # Or just
    initialize_app()

The API for sending messages is now under the ``firebase-admin`` package; hence,
we removed the methods ``send_data_message`` from the QuerySet and class instance
methods. Instead, everything is under a single method: ``send_message``

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    FCMDevice.objects.send_message(Message(data=dict()))
    # Note: You can also combine the data and notification kwarg
    FCMDevice.objects.send_message(
        Message(notification=Notification(title="title", body="body", image="image_url"))
    )
    device = FCMDevice.objects.first()
    device.send_message(Message(...))

Legacy helper mapping
---------------------

If you are upgrading from ``fcm-django<1`` and still import helpers from
``fcm_django.fcm``, those helpers are gone in the ``firebase-admin`` based
releases.

- ``fcm_send_bulk_message(...)`` becomes ``FCMDevice.objects.send_message(Message(...))``
- ``fcm_send_message(...)`` becomes ``device.send_message(Message(...))``
- ``send_data_message(...)`` is folded into ``send_message(...)`` by passing
  a ``Message(data=...)`` payload

The old ``title=...`` / ``body=...`` kwargs are now expressed via
``firebase_admin.messaging.Notification``:

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    from fcm_django.models import FCMDevice

    FCMDevice.objects.send_message(
        Message(
            notification=Notification(title="title", body="body"),
            data={"key": "value"},
        )
    )

For topic subscriptions, topic sends, and the additional sending parameters
``skip_registration_id_lookup`` and ``additional_registration_ids``, see
`Sending Messages <https://github.com/xtrinch/fcm-django#sending-messages>`_.

Note: ``registration_ids`` is actually incorrect terminology as it
should actually be called ``registration tokens``. However, to be
consistent with ``django-push-notifications``, we've refrained from
switching to stay backwards compatible in the docs and with the
sister package.
