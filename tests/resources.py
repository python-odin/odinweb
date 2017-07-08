import odin


class User(odin.Resource):
    id = odin.IntegerField()
    name = odin.StringField()
    email = odin.EmailField(null=True)
