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

For topic subscriptions, topic sends, and the additional sending parameters
``skip_registration_id_lookup`` and ``additional_registration_ids``, see
`Sending Messages <https://github.com/xtrinch/fcm-django#sending-messages>`_.

Note: ``registration_ids`` is actually incorrect terminology as it
should actually be called ``registration tokens``. However, to be
consistent with ``django-push-notifications``, we've refrained from
switching to stay backwards compatible in the docs and with the
sister package.
