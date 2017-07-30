=======
OdinWeb
=======

A Restful API framework for Python that uses Odin Resources with native support for `Swagger <https://swagger.io>`_
and an integrated Swagger-UI.

.. image:: https://img.shields.io/pypi/l/odinweb.svg?style=flat
    :target: https://pypi.python.org/pypi/odinweb/
    :alt: License

.. image:: https://img.shields.io/pypi/v/odinweb.svg?style=flat
    :target: https://pypi.python.org/pypi/odinweb/

.. image:: https://img.shields.io/travis/python-odin/odinweb/master.svg?style=flat
    :target: https://travis-ci.org/python-odin/odinweb
    :alt: Travis CI Status

.. image:: https://codecov.io/gh/python-odin/odinweb/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/python-odin/odinweb
    :alt: Code cov

.. image:: https://landscape.io/github/python-odin/odinweb/master/landscape.svg?style=flat
   :target: https://landscape.io/github/python-odin/odinweb/master
   :alt: Code Health

.. image:: https://img.shields.io/requires/github/python-odin/odinweb.svg?style=flat
    :target: https://requires.io/github/python-odin/odinweb/requirements/?branch=master
    :alt: Requirements Status

.. image:: https://img.shields.io/badge/gitterim-timsavage.odin-brightgreen.svg?style=flat
    :target: https://gitter.im/timsavage/odin
    :alt: Gitter.im

The initial development effort currently supports:

- `Flask <http://flask.pocoo.org/>`_
- `Bottle <https://bottlepy.org>`_
- `Django <https://wwww.djangoproject.org/>`_ - Odin/Django integration is already implemented with
  `baldr <https://github.com/python-odin/baldr>`_. Odin Web is an evolution of the design of baldr. Baldr still includes
  other integration between django and odin, once merged Baldr will be depreciated

With the following frameworks to be included once a stable API is established:

- `Retort <https://github.com/timsavage/retort>`_ - A Flask/Bottle like framework for AWS Lambda/API Gateway

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
    # or
    git clone git@github.com:python-odin/odinweb.django.git

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

    USERS = [
        User(1, 'pimpstar24', 'Bender', 'Rodreges', 'bender@ilovebender.com'),
        User(2, 'zoidberg', 'Zoidberg', '', 'zoidberg@freemail.web'),
        User(3, 'amylove79', 'Amy', 'Wong', 'awong79@marslink.web'),
    ]
    USER_ID = len(USERS)


    class UserApi(api.ResourceApi):
        resource = User
        tags = ['user']

        @api.listing
        def get_user_list(self, request, offset, limit):
            return USERS[offset:offset+limit], len(USERS)

        @api.create
        def create_user(self, request, user):
            global USER_ID

            # Add user to list
            USER_ID += 1
            user.id = USER_ID
            USERS.append(user)

            return user

        @api.detail
        def get_user(self, request, resource_id):
            """
            Get a user object
            """
            for user in USERS:
                if user.id == resource_id:
                    return user

            raise api.Error.from_status(api.HTTPStatus.NOT_FOUND)

        @api.delete
        def delete_user(self, request, resource_id):
            for idx, user in enumerate(USERS):
                if user.id == resource_id:
                    USERS.remove(user)
                    return api.create_response(200)

            raise api.Error.from_status(api.HTTPStatus.NOT_FOUND)

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

