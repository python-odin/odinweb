import odin


class User(odin.Resource):
    class Meta:
        namespace = 'tests'

    id = odin.IntegerField()
    name = odin.StringField()
    email = odin.EmailField(null=True, doc_text="Users email")
    role = odin.StringField(null=True, choices=(
        ('admin', 'Admin'),
        ('manager', 'Manage'),
        ('user', 'User'),
    ))


class Group(odin.Resource):
    class Meta:
        namespace = 'tests'

    group_id = odin.IntegerField(key=True)
    name = odin.StringField()

    @odin.calculated_field
    def title(self):
        return self.name.title()
