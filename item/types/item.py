from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, GameLog, User, locked_by_self
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto
from strawberry_django_plus.mutations import resolvers
from django.utils import timezone

from .. import models

if TYPE_CHECKING:
    from item.types import Artifact


@gql.django.type(models.ArmorTraits)
class ArmorTraits(relay.Node):
    ac_bonus: auto


@gql.django.input(models.ArmorTraits)
class ArmorTraitsInput:
    ac_bonus: auto
    delete: Optional[bool] = False


@gql.django.type(models.WeaponTraits)
class WeaponTraits(relay.Node):
    attack_bonus: auto


@gql.django.input(models.WeaponTraits)
class WeaponTraitsInput:
    attack_bonus: auto
    delete: Optional[bool] = False


@gql.django.type(models.EquipmentTraits)
class EquipmentTraits(relay.Node):
    brief_description: auto


@gql.django.input(models.EquipmentTraits)
class EquipmentTraitsInput:
    brief_description: auto
    delete: Optional[bool] = False


@gql.django.type(models.Item)
class Item(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    locked_by_self: bool = gql.field(resolver=locked_by_self)
    artifacts: relay.Connection[
        Annotated["Artifact", gql.lazy("item.types")]
    ] = gql.django.connection()
    armor: Optional[ArmorTraits]
    weapon: Optional[WeaponTraits]
    equipment: Optional[EquipmentTraits]


@gql.django.input(models.Item)
class ItemInput(EntityInput):
    artifacts: auto
    armor: Optional[ArmorTraitsInput]
    weapon: Optional[WeaponTraitsInput]
    equipment: Optional[EquipmentTraitsInput]


@gql.django.partial(models.Item)
class ItemInputPartial(EntityInput, gql.NodeInput):
    artifacts: auto
    armor: Optional[ArmorTraitsInput]
    weapon: Optional[WeaponTraitsInput]
    equipment: Optional[EquipmentTraitsInput]


@gql.type
class ItemQuery:
    item: Optional[Item] = gql.django.field()
    items: relay.Connection[Item] = gql.django.connection()

    @gql.django.connection
    def Items_connection_filtered(self, name_startswith: str) -> Iterable[Item]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Item.objects.filter(name__startswith=name_startswith)


@gql.type
class ItemMutation:
    @gql.django.mutation(permission_classes=[IsStaff])
    def create_item(self, info, input: ItemInput) -> Item:
        """
        Create an item with traits if present.
        """

        # Collect data from input
        data = vars(input)
        armor_data = data.pop("armor", None)
        weapon_data = data.pop("weapon", None)
        equipment_data = data.pop("equipment", None)

        # Create item
        item = resolvers.create(info, models.Item, resolvers.parse_input(info, data))

        # Create traits if present and assign to the item
        if armor_data:
            armor_data = vars(armor_data)
            armor_data["item"] = item
            armor = resolvers.create(info, models.ArmorTraits, armor_data)
            item.armor = armor
        if weapon_data:
            weapon_data = vars(weapon_data)
            weapon_data["item"] = item
            weapon = resolvers.create(info, models.WeaponTraits, weapon_data)
            item.weapon = weapon
        if equipment_data:
            equipment_data = vars(equipment_data)
            equipment_data["item"] = item
            equipment = resolvers.create(info, models.EquipmentTraits, equipment_data)
            item.equipment = equipment

        # Return the item
        return item

    @gql.django.mutation(permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked])
    def update_item(self, info, input: ItemInputPartial) -> Item:
        # Collect data from input
        data = vars(input)
        node_id: gql.relay.GlobalID = data.pop("id")
        armor_data = data.pop("armor", None)
        weapon_data = data.pop("weapon", None)
        equipment_data = data.pop("equipment", None)
        item: models.Item = node_id.resolve_node(info, ensure_type=models.Item)

        # Update item
        resolvers.update(info, item, resolvers.parse_input(info, data))

        # Create or update traits if present and assign to the item
        if armor_data:
            armor_data = vars(armor_data)
            delete_armor = armor_data.pop("delete", False)
            if delete_armor:
                if hasattr(item, "armor"):
                    item.armor.delete()
                    item.armor = None
            elif hasattr(item, "armor"):
                resolvers.update(info, item.armor, armor_data)
            else:
                armor_data["item"] = item
                armor = resolvers.create(info, models.ArmorTraits, armor_data)
                item.armor = armor

        if weapon_data:
            weapon_data = vars(weapon_data)
            delete_weapon = weapon_data.pop("delete", False)
            if delete_weapon:
                if hasattr(item, "weapon"):
                    item.weapon.delete()
                    item.weapon = None
            elif hasattr(item, "weapon"):
                resolvers.update(info, item.weapon, weapon_data)
            else:
                weapon_data["item"] = item
                weapon = resolvers.create(info, models.WeaponTraits, weapon_data)
                item.weapon = weapon

        if equipment_data:
            equipment_data = vars(equipment_data)
            delete_equipment = equipment_data.pop("delete", False)
            if delete_equipment:
                if hasattr(item, "equipment"):
                    item.equipment.delete()
                    item.equipment = None
            elif hasattr(item, "equipment"):
                resolvers.update(info, item.equipment, equipment_data)
            else:
                equipment_data["item"] = item
                equipment = resolvers.create(
                    info, models.EquipmentTraits, equipment_data
                )
                item.equipment = equipment

        # Release lock if user is the lock user
        item.release_lock(info.context.request.user)

        # Return the item
        return item

    delete_item: Item = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def item_add_image(self, info, id: gql.relay.GlobalID, image_id: str) -> Item:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def item_lock(self, info, id: gql.relay.GlobalID) -> Item:
        item = id.resolve_node(info)
        item = item.lock(info.context.request.user)
        return item

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def item_release_lock(self, info, id: gql.relay.GlobalID) -> Item:
        item = id.resolve_node(info)
        item = item.release_lock(info.context.request.user)
        return item
