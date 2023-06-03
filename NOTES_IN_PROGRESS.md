Game log connections?

CHOICES ENUMS: Switch to one of the ways here? https://blb-ventures.github.io/strawberry-django-plus/quickstart/

May need to figure how whether and how to have a front-facing admin site from the django backend server.

CURRENTLY TRYING TO USE strawberry-django-auth to integrate jwt auth.
: I think this is mostly working
: I'm currently returning the same value as the library's token_auth mutation
: It looks like I need to include the token in the headers as { authorization: `JWT ${token}` }
: I'll also want to remove/comment out more strawberry-django-auth mutations that I'm not using and I don't want to expose
: For the client, I'll need to refresh the token when it expires, including `revoke_refresh_token` along with `refresh_token` to make sure the old token is no longer valid

NEED to complete moving `npcs` to `characters`. Probably need to rename current `Character` model to something else first (`PlayerCharacter`?), then rename `NPC` to `Character`.

BEFORE DEPLOYMENT
Add GOOGLE_SSO_CLIENT_ID and GOOGLE_SSO_CLIENT_SECRET to environment variables
In houdini, make sure it's pulling the schema from the right place depending on the environment

GAMELOG LIST PAGE IDEAS
title – like an episode title
link (url)
game date
brief summary (brief, a sentence or two)
longer summary (synopsis, a paragraph or two) – under an expandable section?
settings (different from place logs, since a place might be mentioned in a log without being the setting for the log)

SEARCH? — it'd be great to have these searchable. Might even include the full text of the log in the search, but that might be too much. A separate index probably.

GAMELOG DETAIL PAGE IDEAS
title
link (url)
game date
brief summary (a sentence or two)
longer summary (a paragraph or two)
settings
characters? more?

CURRENTLY WORKING ON
Adding settings to gamelogs
Need to create and run migrations

<!-- > > > from nucleus.ai_helpers import openai_summarize_text_chat -->

> > > from nucleus.ai_helpers import openai_shorten_text

<!-- > > > from nucleus.ai_helpers import openai_summarize_text -->

> > > from nucleus.gdrive import fetch_airel_file_text
> > > log = GameLog.objects.first()
> > > text = fetch_airel_file_text(log.google_id)
> > > response = openai_shorten_text(text)

<!-- > > > response = openai_summarize_text_chat(text) -->

<!-- > > > response = openai_summarize_text(text) -->
