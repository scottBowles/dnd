import graphene
from graphene import relay
from graphql_relay import from_global_id


class RelayCUD(object):
    def __init__(self, field, Node, Input, model, serializer_class, **kwargs):
        self.field = field
        self.Node = Node
        self.Input = Input
        self.model = model
        self.serializer_class = serializer_class

    def get_django_id(self, id):
        return from_global_id(id)[1]

    def get_serializer_class(self):
        return self.serializer_class

    def get_model(self):
        return self.model

    def get_instance(self, info, global_id):
        id = self.get_django_id(global_id)
        return self.model.objects.get(id=id)

    def create(self, info, **input):
        serializer = self.serializer_class(data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def update(self, info, **input):
        instance = self.get_instance(info, input["id"])
        input["id"] = self.get_django_id(input["id"])
        serializer = self.serializer_class(instance, data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def partial_update(self, info, **input):
        instance = self.get_instance(info, input["id"])
        input["id"] = self.get_django_id(input["id"])
        serializer = self.serializer_class(instance, data=input, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def delete(self, info, **input):
        instance = self.get_instance(info, input["id"])
        instance.delete()
        return instance

    def get_mixin(self, action, Input, include_field=True):
        field = self.field
        Node = self.Node
        _Input = Input

        class MutationMixin:
            ok = graphene.Boolean()
            errors = graphene.String()

            class Input(_Input):
                pass

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
        Mixin = self.get_mixin(self.create, self.Input)
        mixin_name = self.field.title() + "CreateMutation"
        return type(mixin_name, (Mixin, relay.ClientIDMutation), {})

    def update_mutation(self):
        class Input(self.Input):
            id = graphene.ID()

        Mixin = self.get_mixin(self.update, Input)
        mixin_name = self.field.title() + "UpdateMutation"
        return type(mixin_name, (Mixin, relay.ClientIDMutation), {})

    def patch_mutation(self):
        class Input(self.Input):
            id = graphene.ID()

        Mixin = self.get_mixin(self.partial_update, Input)
        mixin_name = self.field.title() + "PatchMutation"
        return type(mixin_name, (Mixin, relay.ClientIDMutation), {})

    def delete_mutation(self):
        class Input:
            id = graphene.ID()

        Mixin = self.get_mixin(self.delete, Input, include_field=False)
        mixin_name = self.field.title() + "DeleteMutation"
        return type(mixin_name, (Mixin, relay.ClientIDMutation), {})

    def get_mutation_class(self):
        class Mutation(graphene.ObjectType):
            pass

        setattr(Mutation, self.field + "_create", self.create_mutation().Field())
        setattr(Mutation, self.field + "_update", self.update_mutation().Field())
        setattr(Mutation, self.field + "_patch", self.patch_mutation().Field())
        setattr(Mutation, self.field + "_delete", self.delete_mutation().Field())

        return Mutation
