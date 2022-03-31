import graphene
from graphene import relay
from graphql_relay import from_global_id
from graphql_jwt.decorators import login_required
from rest_framework import serializers


class RelayPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    PrimaryKeyRelatedField that converts incoming global ids to internal ids.
    """

    def to_internal_value(self, data):
        return super().to_internal_value(from_global_id(data)[1])


class RelayModelSerializer(serializers.ModelSerializer):
    """
    ModelSerializer that accepts global ids for foreign keys.
    """

    serializer_related_field = RelayPrimaryKeyRelatedField


# decorator for get_queryset that returns queryset.none() is user is not authenticated
def login_or_queryset_none(func):
    def wrapper(cls, queryset, info):
        if info.context.user.is_authenticated:
            return func(cls, queryset, info)
        return queryset.none()

    return wrapper


class RelayCUD(object):
    actions = ("create", "update", "patch", "delete")

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

    def prepare_inputs(self, info, **input):
        return input

    def get_mutation_base(self, action, Input, include_field=True):
        field = self.field
        Node = self.Node
        _Input = Input
        prepare_inputs = self.prepare_inputs

        class MutationBase:
            ok = graphene.Boolean()
            errors = graphene.String()

            class Input(_Input):
                pass

            @classmethod
            @login_required
            def mutate_and_get_payload(cls, root, info, **input):
                input = prepare_inputs(info, **input)
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

    def get_mutation_name(self, action):
        return f"{self.field}_{action}"

    def get_mutation_class_for_action(self, action):
        return self.__getattribute__(action + "_mutation")()

    def get_mutation_class(self):
        class Mutation(graphene.ObjectType):
            pass

        # By default this adds create, update, patch and delete mutations
        # Override `actions` to limit the mutations (e.g., `actions = ("create", "update")`)
        for action in self.actions:
            mutation_name = self.get_mutation_name(action)
            mutation_class = self.get_mutation_class_for_action(action)
            setattr(
                Mutation,
                mutation_name,
                mutation_class.Field(),
            )

        return Mutation

    class Meta:
        abstract = True
