from django import forms
from django_registration.forms import RegistrationForm
from django_registration.validators import DEFAULT_RESERVED_NAMES

from users.models import ProfileLink, User


class UserRegistrationForm(RegistrationForm):
    reserved_names = DEFAULT_RESERVED_NAMES + [
        # shortcuts
        "account",
        "api",
        "campaign",
        "campaigns",
        "class",
        "classes",
        "help",
        "magic",
        "magic_item",
        "magic_items",
        "magicitem",
        "magicitems",
        "mine",
        "monster",
        "monsters",
        "notebook",
        "notebooks",
        "profile",
        "search",
        "settings",
        "spell",
        "spells",
        "statblock",
        "statblocks",
        "wiki",
        "wikis",

        # classes
        "artificer",
        "barbarian",
        "bard",
        "cleric",
        "druid",
        "fighter",
        "monk",
        "paladin",
        "ranger",
        "rogue",
        "sorcerer",
        "warlock",
        "wizard",

        # roles
        "dm",
        "dungeon_master",
        "dungeonmaster",
        "game_master",
        "gamemaster",
        "gm",
        "judge",
        "keeper",
        "mc",
        "narrator",
        "referee",
        "storyteller",
        "warden",

        # official sounding
        "5e",
        "a5e",
        "criticalrole",
        "critical_role",
        "dnd",
        "dndbeyond",
        "enpublishing",
        "en_publishing",
        "hasbro",
        "koboldpress",
        "kobold_press",
        "levelup",
        "levelup5e",
        "level_up",
        "mcdm",
        "onednd",
        "one_dnd",
        "paizo",
        "pathfinder",
        "pf2e",
        "rules",
        "rules_lawyer",
        "ruleslawyer",
        "srd",
        "talesofthevaliant",
        "tales_of_the_valiant",
        "tov",
        "wizards",
        "wizardsofthecoast",
        "wotc",
        "your5e",
        "your5eofficial",

        # generic terms
        "character",
        "npc",
        "npcs",
        "party",
        "pc",
        "pcs",
        "player",
        "players",
        "playercharacter",
        "playercharacters",
    ]

    class Meta(RegistrationForm.Meta):
        model = User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "short_name", "description"]


class ProfileLinkForm(forms.ModelForm):
    class Meta:
        model = ProfileLink
        fields = ["url", "label"]
