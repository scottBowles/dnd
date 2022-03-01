import graphene
from graphene import relay
from graphql_relay import from_global_id
from rest_framework import serializers


class RelayPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        return super().to_internal_value(from_global_id(data)[1])


class RelayCUD(object):
    def __init__(self, *args, **kwargs):
        for el in ["field", "Node", "model", "serializer_class"]:
            if not hasattr(self, el):
                raise ValueError("Missing required attribute: {}".format(el))
        super().__init__(*args, **kwargs)

    class IdentifyingInput:
        id = graphene.ID()

    def get_django_id(self, id):
        return from_global_id(id)[1]

    def get_serializer_class(self):
        return self.serializer_class

    def get_model(self):
        return self.model

    def get_instance(self, info, input):
        id = self.get_django_id(input["id"])
        return self.model.objects.get(id=id)

    def create(self, info, **input):
        serializer = self.serializer_class(data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def update(self, info, **input):
        instance = self.get_instance(info, input)
        serializer = self.serializer_class(instance, data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def partial_update(self, info, **input):
        instance = self.get_instance(info, input)
        serializer = self.serializer_class(instance, data=input, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def delete(self, info, **input):
        instance = self.get_instance(info, input)
        instance.delete()
        return instance

    def get_mutation_base(self, action, Input, include_field=True):
        field = self.field
        Node = self.Node
        _Input = Input

        class MutationBase:
            ok = graphene.Boolean()
            errors = graphene.String()

            class Input(_Input):
                pass

            @classmethod
            def mutate_and_get_payload(cls, root, info, **input):
                instance = action(info, **input)
                args = {"ok": True}
                if include_field:
                    args[field] = instance
                return cls(**args)

        if include_field:
            setattr(MutationBase, field, graphene.Field(Node))

        return MutationBase

    def create_mutation(self):
        MutationBase = self.get_mutation_base(self.create, self.Input)
        mutation_class_name = self.field.title() + "CreateMutation"
        return type(mutation_class_name, (MutationBase, relay.ClientIDMutation), {})

    def update_mutation(self):
        class Input(self.IdentifyingInput, self.Input):
            pass

        Mixin = self.get_mutation_base(self.update, Input)
        mutation_class_name = self.field.title() + "UpdateMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})

    def patch_mutation(self):
        class Input(self.IdentifyingInput, self.Input):
            pass

        Mixin = self.get_mutation_base(self.partial_update, Input)
        mutation_class_name = self.field.title() + "PatchMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})

    def delete_mutation(self):
        Mixin = self.get_mutation_base(
            self.delete, self.IdentifyingInput, include_field=False
        )
        mutation_class_name = self.field.title() + "DeleteMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})

    def get_mutation_class(self):
        class Mutation(graphene.ObjectType):
            pass

        setattr(Mutation, self.field + "_create", self.create_mutation().Field())
        setattr(Mutation, self.field + "_update", self.update_mutation().Field())
        setattr(Mutation, self.field + "_patch", self.patch_mutation().Field())
        setattr(Mutation, self.field + "_delete", self.delete_mutation().Field())

        return Mutation

    class Meta:
        abstract = True
