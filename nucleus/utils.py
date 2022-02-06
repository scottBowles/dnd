import graphene
from graphene import relay
from graphql_relay import from_global_id


class RelayCUD(object):
    def __init__(self, field, Node, **kwargs):
        self.field = field
        self.Node = Node

    def get_django_id(self, id):
        return from_global_id(id)[1]

    def get_serializer_class(self):
        return self.Meta.serializer

    def get_model(self):
        return self.Meta.model

    def get_instance(self, info, global_id):
        id = self.get_django_id(global_id)
        model = self.get_model()
        return model.objects.get(id=id)

    def create(self, info, **input):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def update(self, info, **input):
        instance = self.get_instance(info, input["id"])
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(instance, data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def delete(self, info, **input):
        instance = self.get_instance(info, input["id"])
        instance.delete()
        return instance

    def get_mutation_mixin(self, action, include_field=True):
        field = self.field
        Node = self.Node

        class MutationMixin(relay.ClientIDMutation):
            ok = graphene.Boolean()
            errors = graphene.String()

            @classmethod
            def mutate_and_get_payload(cls, root, info, **input):
                try:
                    instance = action(info, **input)
                    args = {"ok": True, "errors": None}
                    if include_field:
                        args[field] = instance
                    return cls(**args)
                except Exception as e:
                    args = {"ok": False, "errors": str(e)}
                    if include_field:
                        args[field] = None
                    return cls(**args)

        if include_field:
            setattr(MutationMixin, field, graphene.Field(Node))

        return MutationMixin

    def create_mutation(self):
        MutationMixin = self.get_mutation_mixin(self.create)
        _Input = self.Input

        class Create(MutationMixin):
            class Input(_Input):
                pass

        return Create

    def update_mutation(self):
        MutationMixin = self.get_mutation_mixin(self.update)
        _Input = self.Input

        class Update(MutationMixin):
            class Input(_Input):
                id = graphene.ID()

        return Update

    def delete_mutation(self):
        MutationMixin = self.get_mutation_mixin(self.delete, include_field=False)

        class Delete(MutationMixin):
            class Input:
                id = graphene.ID()

        return Delete
