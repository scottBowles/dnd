import graphene
from graphene import relay
from graphql_relay import from_global_id
from graphql_jwt.decorators import login_required
from rest_framework import serializers
from nucleus.exceptions import ConcurrencyLockException


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


class MutationsCreatorMixin:
    class IdentifyingInput:
        id = graphene.ID()

    def get_django_id(self, id):
        return from_global_id(id)[1]

    def get_model(self):
        return self.model

    def get_instance(self, info, input):
        id = self.get_django_id(input["id"])
        return self.model.objects.get(id=id)

    def prepare_inputs(self, info, **input):
        return input

    def get_mutation_base(self, action, Input, include_field=True):
        field = self.field
        Node = getattr(self, "Node", None)
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


class ConcurrencyLockActions(MutationsCreatorMixin):
    actions = ("lock", "release_lock")
    _required_attributes = ("field", "Node", "model")

    def __init__(self, *args, **kwargs):
        for el in self._required_attributes:
            if not hasattr(self, el):
                raise ValueError("Missing required attribute: {}".format(el))
        super().__init__(*args, **kwargs)

    def lock(self, info, **input):
        instance = self.get_instance(info, input)
        instance = instance.lock(info.context.user)
        return instance

    def release_lock(self, info, **input):
        instance = self.get_instance(info, input)
        instance = instance.release_lock(info.context.user)
        return instance

    def lock_mutation(self):
        Mixin = self.get_mutation_base(self.lock, self.IdentifyingInput)
        mutation_class_name = self.field.title() + "LockMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})

    def release_lock_mutation(self):
        Mixin = self.get_mutation_base(self.release_lock, self.IdentifyingInput)
        mutation_class_name = self.field.title() + "ReleaseLockMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})


class ImageMutations(MutationsCreatorMixin):
    actions = ("add_image",)
    _required_attributes = ("field", "Node", "model")

    def __init__(self, *args, **kwargs):
        for el in self._required_attributes:
            if not hasattr(self, el):
                raise ValueError("Missing required attribute: {}".format(el))
        super().__init__(*args, **kwargs)

    def add_image(self, info, **input):
        instance = self.get_instance(info, input)
        imageId = input["image_id"]
        instance.add_image(imageId)
        return instance

    def add_image_mutation(self):
        class Input(self.IdentifyingInput):
            image_id = graphene.String()

        Mixin = self.get_mutation_base(self.add_image, Input)
        mutation_class_name = self.field.title() + "AddImageMutation"
        return type(mutation_class_name, (Mixin, relay.ClientIDMutation), {})


class RelayCUD(MutationsCreatorMixin):
    actions = ("create", "update", "patch", "delete")
    _required_attributes = ("field", "Node", "model", "serializer_class")
    enforce_lock = False

    def __init__(self, *args, **kwargs):
        for el in self._required_attributes:
            if not hasattr(self, el):
                raise ValueError("Missing required attribute: {}".format(el))
        super().__init__(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

    def _enforce_lock(self, info, instance):
        if (
            hasattr(instance, "lock_user")
            and instance.lock_user
            and instance.lock_user != info.context.user
        ):
            raise ConcurrencyLockException(
                f"{self.field.title()} is locked by another user: {instance.lock_user}."
            )

    def create(self, info, **input):
        serializer = self.serializer_class(data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def update(self, info, **input):
        instance = self.get_instance(info, input)
        if self.enforce_lock:
            self._enforce_lock(info, instance)
        serializer = self.serializer_class(instance, data=input)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if self.enforce_lock:
            instance.release_lock(info.context.user)
        return instance

    def partial_update(self, info, **input):
        instance = self.get_instance(info, input)
        if self.enforce_lock:
            self._enforce_lock(info, instance)
        serializer = self.serializer_class(instance, data=input, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if self.enforce_lock:
            instance.release_lock(info.context.user)
        return instance

    def delete(self, info, **input):
        instance = self.get_instance(info, input)
        if self.enforce_lock:
            self._enforce_lock(info, instance)
        instance.delete()
        return instance

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

    class Meta:
        abstract = True
