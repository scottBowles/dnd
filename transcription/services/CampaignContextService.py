from datetime import timedelta
from typing import Any, Dict, List
from django.db.models import Max
from django.utils import timezone

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from place.models import Place
from race.models import Race

from datetime import timedelta
from typing import Any, Dict, List
from .TranscriptionConfig import TranscriptionConfig


class CampaignContextService:
    """Service for fetching and formatting campaign context from database."""

    def __init__(self, config: TranscriptionConfig):
        """Initialize with configuration instance."""
        self.config = config

    def get_campaign_context(self, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relevant D&D campaign context from the database.
        Prioritizes entities that have been recently mentioned in game logs.
        """
        context = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        try:
            # Calculate recent threshold
            recent_threshold = timezone.now() - timedelta(
                days=self.config.recent_threshold_days
            )

            def get_entities_by_recency(model, entity_limit):
                """Helper to get entities ordered by recent log mentions."""
                return model.objects.annotate(
                    most_recent_log_date=Max("logs__game_date")
                ).order_by("-most_recent_log_date", "name")[:entity_limit]

            # Get Characters (NPCs)
            characters = get_entities_by_recency(Character, 20)
            for char in characters:
                char_info = {
                    "name": char.name,
                    "race": char.race.name if char.race else None,
                    "description": char.description[:100] if char.description else "",
                    "recently_mentioned": bool(
                        char.most_recent_log_date
                        and char.most_recent_log_date >= recent_threshold
                    ),
                }
                context["characters"].append(char_info)

            # Get Places
            places = get_entities_by_recency(Place, 15)
            for place in places:
                place_info = {
                    "name": place.name,
                    "type": getattr(place, "place_type", None),
                    "description": place.description[:100] if place.description else "",
                    "recently_mentioned": bool(
                        place.most_recent_log_date
                        and place.most_recent_log_date >= recent_threshold
                    ),
                }
                context["places"].append(place_info)

            # Get Races
            races = get_entities_by_recency(Race, 12)
            for race in races:
                race_info = {
                    "name": race.name,
                    "description": race.description[:100] if race.description else "",
                    "recently_mentioned": bool(
                        race.most_recent_log_date
                        and race.most_recent_log_date >= recent_threshold
                    ),
                }
                context["races"].append(race_info)

            # Get Items
            items = get_entities_by_recency(Item, 12)
            for item in items:
                item_info = {
                    "name": item.name,
                    "description": item.description[:80] if item.description else "",
                    "recently_mentioned": bool(
                        item.most_recent_log_date
                        and item.most_recent_log_date >= recent_threshold
                    ),
                }
                context["items"].append(item_info)

            # Get Artifacts
            artifacts = get_entities_by_recency(Artifact, 8)
            for artifact in artifacts:
                artifact_info = {
                    "name": artifact.name,
                    "type": "artifact",
                    "description": (
                        artifact.description[:80] if artifact.description else ""
                    ),
                    "recently_mentioned": bool(
                        artifact.most_recent_log_date
                        and artifact.most_recent_log_date >= recent_threshold
                    ),
                }
                context["items"].append(artifact_info)

            # Get Associations
            associations = get_entities_by_recency(Association, 12)
            for assoc in associations:
                assoc_info = {
                    "name": assoc.name,
                    "description": assoc.description[:100] if assoc.description else "",
                    "recently_mentioned": bool(
                        assoc.most_recent_log_date
                        and assoc.most_recent_log_date >= recent_threshold
                    ),
                }
                context["associations"].append(assoc_info)

        except Exception as e:
            print(f"Warning: Could not fetch database context: {e}")
            print("Continuing without database context...")

        return context

    def get_formatted_context(self, max_length: int = 800) -> str:
        """
        Get campaign context from database and format it for Whisper prompt.
        Prioritizes recently mentioned entities.
        """
        context = self.get_campaign_context()
        return self._format_context_for_prompt(context, max_length)

    def _format_context_for_prompt(
        self, context: Dict[str, List[Dict[str, Any]]], max_length: int = 1200
    ) -> str:
        """
        Format the campaign context into a concise string for the Whisper prompt.
        Prioritizes recently mentioned entities.
        """
        prompt_parts = []

        def get_prioritized_names(entities, max_count):
            """Sort by recently_mentioned first, then by name."""
            sorted_entities = sorted(
                entities,
                key=lambda x: (not x.get("recently_mentioned", False), x["name"]),
            )
            return [entity["name"] for entity in sorted_entities[:max_count]]

        # Character names (highest priority)
        if context["characters"]:
            recent_chars = []
            other_chars = []

            for char in context["characters"][:20]:
                name = char["name"]
                if char.get("race"):
                    name += f" ({char['race']})"

                if char.get("recently_mentioned"):
                    recent_chars.append(name)
                else:
                    other_chars.append(name)

            all_char_names = recent_chars[:10] + other_chars[:5]
            if all_char_names:
                prompt_parts.append(f"Key Characters: {', '.join(all_char_names)}")

        # Place names
        if context["places"]:
            place_names = get_prioritized_names(context["places"], 8)
            if place_names:
                prompt_parts.append(f"Important Places: {', '.join(place_names)}")

        # Race names
        if context["races"]:
            race_names = get_prioritized_names(context["races"], 8)
            if race_names:
                prompt_parts.append(f"Races: {', '.join(race_names)}")

        # Items/Artifacts
        if context["items"]:
            artifacts = [
                item for item in context["items"] if item.get("type") == "artifact"
            ]
            regular_items = [
                item for item in context["items"] if item.get("type") != "artifact"
            ]

            item_names = []
            if artifacts:
                artifact_names = get_prioritized_names(artifacts, 4)
                item_names.extend([f"{name} (artifact)" for name in artifact_names])

            if regular_items:
                regular_names = get_prioritized_names(regular_items, 6)
                item_names.extend(regular_names)

            if item_names:
                prompt_parts.append(f"Notable Items: {', '.join(item_names)}")

        # Organizations
        if context["associations"]:
            org_names = get_prioritized_names(context["associations"], 6)
            if org_names:
                prompt_parts.append(f"Organizations: {', '.join(org_names)}")

        # Join and truncate gracefully
        formatted_context = ". ".join(prompt_parts)

        # Handle edge case where max_length is 0 or very small
        if max_length <= 0:
            return ""

        if len(formatted_context) > max_length:
            if max_length < 10:  # Very small max_length
                return "..."

            truncated = formatted_context[:max_length]
            last_period = truncated.rfind(".")
            if last_period > max_length * 0.75:
                formatted_context = truncated[: last_period + 1]
            else:
                last_space = truncated.rfind(" ")
                if last_space > max_length * 0.9:
                    formatted_context = truncated[:last_space] + "..."
                else:
                    formatted_context = truncated + "..."

        return formatted_context
