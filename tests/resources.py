import odin


class User(odin.Resource):
    class Meta:
        namespace = 'tests'

    id = odin.IntegerField()
    name = odin.StringField()
    email = odin.EmailField(null=True)


class Group(odin.Resource):
    class Meta:
        namespace = 'tests'

    id = odin.IntegerField()
    name = odin.StringField()
