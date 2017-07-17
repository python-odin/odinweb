=======
OdinWeb
=======

A Restful API framework for Python that uses Odin Resources with native support for `Swagger <https://swagger.io>`_
and an integrated Swagger-UI.

The initial development effort currently supports:

- `Flask <http://flask.pocoo.org/>`_
- `Bottle <https://bottlepy.org>`_

With the following frameworks to be included once a stable API is established:

- `Retort <https://github.com/timsavage/retort>`_ - A Flask/Bottle like framework for AWS Lambda/API Gateway
- `Django <https://wwww.djangoproject.org/>`_ - Odin/Django integration is already implemented with
    `baldr <https://github.com/python-odin/baldr>`_. Odin Web is an evolution of the design of baldr and will
    be swapped in favour of OdinWeb in the future. Baldr also includes other integration with Django.

There are no plans at this point for other libraries although I'm open to suggestions/contributions. The effort
required to integrate other libraries is minimal as Odin Web was designed to be agnostic of the framework it is
running within.

.. note::
    Odin Web is being developed very much with a view to dropping support for Python 2.7 in the future, back-ported
    versions of several Python 3.x features are utilised in the design (eg :py:mod:`enum` :py:mod:`http`).


Installation
============

An early Alpha release is on PyPI, the API has however undergone significant changes since this was first put out the
best option is to checkout a tagged release from GitHub until a beta is ready that will solidify the API

Install the core library::

    git clone git@github.com:python-odin/odinweb.git
    cd odinweb
    python setup.py install

Install your preferred web framework::

    git clone git@github.com:python-odin/odinweb.flask.git
    # or
    git clone git@github.com:python-odin/odinweb.bottle.git

    # Change into the appropriate directory then
    python setup.py install


Quickstart
==========

Odin Web is very much oriented around Resources so first define your resources::

    import odin

    class User(odin.Resource):
        """
        User resource
        """
        id = odin.IntegerField()
        username = odin.StringField()
        first_name = odin.StringField()
        last_name = odin.StringField()
        email = odin.EmailField()


Next define your API::

    from odinweb import api

    USERS = {
        1: User(1, 'pimpstar24', 'Bender', 'Rodreges', 'bender@ilovebender.com'),
        2: User(2, 'zoidberg', 'Zoidberg', '', 'zoidberg@freemail.web'),
        3: User(3, 'amylove79', 'Amy', 'Wong', 'awong79@marslink.web'),
    }


    class UserApi(api.ResourceApi):
        resource = User

        @api.collection
        def list_users(self, request, offset, limit):
            """
            Get user list
            """
            return USERS[offset:offset+limit], len(USERS)  # Total count of users

        @api.create
        def create_user(self, request, user):
            """
            Create a new user.
            """
            # The user resource is populated and validated by Odin Web
            global USERS

            # Add user to list
            user.id = len(USERS)
            USERS[user.id] = user

            return user

        @api.detail
        def get_user(self, request, resource_id):
            """
            Get a user
            """
            user = USERS.get(resource_id)
            if not user:
                raise api.Error.from_status(api.HTTPStatus.NOT_FOUND)
            return user

This defines an API for listing, fetching and creating a users.

Finally hookup to your web framework, in this case Flask and enable swagger spec::

    from flask import Flask
    from odinweb.flask import ApiBlueprint
    from odinweb.swagger import SwaggerSpec

    app = flask.Flask(__name__)

    app.register_blueprint(
        ApiBlueprint(
            # Use an API version
            api.ApiVersion(
                SwaggerSpec('Flask Example API', enable_ui=True),  # Support for Swagger!
                UserApi(),
            ),
            debug_enabled=True,  # Enable debug output
        ),
    )

Start the flask app and you can browse to the swagger UI to try out the API::

    http://localhost:5000/api/v1/swagger/ui

