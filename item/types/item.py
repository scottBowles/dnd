from typing import TYPE_CHECKING, Annotated, Iterable, Optional

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection
from nucleus.types import Entity, EntityInput, EntityInputPartial

from .. import models

if TYPE_CHECKING:
    from item.types import Artifact, Item


@strawberry_django.type(models.ArmorTraits)
class ArmorTraits(relay.Node):
    ac_bonus: auto


@strawberry_django.input(models.ArmorTraits)
class ArmorTraitsInput:
    ac_bonus: auto
    delete: Optional[bool] = False


@strawberry_django.type(models.WeaponTraits)
class WeaponTraits(relay.Node):
    attack_bonus: auto


@strawberry_django.input(models.WeaponTraits)
class WeaponTraitsInput:
    attack_bonus: auto
    delete: Optional[bool] = False


@strawberry_django.type(models.EquipmentTraits)
class EquipmentTraits(relay.Node):
    brief_description: auto


@strawberry_django.input(models.EquipmentTraits)
class EquipmentTraitsInput:
    brief_description: auto
    delete: Optional[bool] = False


@strawberry_django.type(models.Item)
class Item(Entity, relay.Node):
    artifacts: DjangoListConnection[
        Annotated["Artifact", strawberry.lazy("item.types")]
    ] = strawberry_django.connection()
    armor: Optional[ArmorTraits] = strawberry_django.field(
        resolver=lambda self, info: getattr(self, "armor", None)
    )
    weapon: Optional[WeaponTraits] = strawberry_django.field(
        resolver=lambda self, info: getattr(self, "weapon", None)
    )
    equipment: Optional[EquipmentTraits] = strawberry_django.field(
        resolver=lambda self, info: getattr(self, "equipment", None)
    )


@strawberry_django.input(models.Item)
class ItemInput(EntityInput):
    artifacts: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto
    armor: Optional[ArmorTraitsInput]
    weapon: Optional[WeaponTraitsInput]
    equipment: Optional[EquipmentTraitsInput]


@strawberry_django.partial(models.Item)
class ItemInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    artifacts: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto
    armor: Optional[ArmorTraitsInput]
    weapon: Optional[WeaponTraitsInput]
    equipment: Optional[EquipmentTraitsInput]


@strawberry.type
class ItemQuery:
    items: DjangoListConnection[Item] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Item])
    # def items_connection_filtered(self, name_startswith: str) -> Iterable[Item]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Item.objects.filter(name__startswith=name_startswith)


@strawberry.type
class ItemMutation:
    @strawberry_django.mutation(permission_classes=[IsStaff])
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

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_item(self, info, input: ItemInputPartial) -> Item:
        # Collect data from input
        data = vars(input)
        node_id: strawberry.relay.GlobalID = data.pop("id")
        armor_data = data.pop("armor", None)
        weapon_data = data.pop("weapon", None)
        equipment_data = data.pop("equipment", None)
        item: models.Item = node_id.resolve_node_sync(info, ensure_type=models.Item)

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

        # Update and return the item
        item = resolvers.update(info, item, resolvers.parse_input(info, data))

        # Release lock if user is the lock user
        item.release_lock(info.context.request.user)

        return item

    delete_item: Item = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def item_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Item:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def item_lock(self, info, id: strawberry.relay.GlobalID) -> Item:
        item = id.resolve_node_sync(info)
        item = item.lock(info.context.request.user)
        return item

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def item_release_lock(self, info, id: strawberry.relay.GlobalID) -> Item:
        item = id.resolve_node_sync(info)
        item = item.release_lock(info.context.request.user)
        return item
