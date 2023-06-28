CHOICES ENUMS: Switch to one of the ways here? https://blb-ventures.github.io/strawberry-django-plus/quickstart/

CURRENTLY TRYING TO USE strawberry-django-auth to integrate jwt auth.
: I'll also want to remove/comment out more strawberry-django-auth mutations that I'm not using and I don't want to expose

SEARCH? — it'd be great to have these searchable. Might even include the full text of the log in the search, but that might be too much. A separate index probably.

<!-- > > > from nucleus.ai_helpers import openai_summarize_text_chat -->

> > > from nucleus.ai_helpers import openai_shorten_text

<!-- > > > from nucleus.ai_helpers import openai_summarize_text -->

> > > from nucleus.gdrive import fetch_airel_file_text
> > > log = GameLog.objects.first()
> > > text = fetch_airel_file_text(log.google_id)
> > > response = openai_shorten_text(text)

<!-- > > > response = openai_summarize_text_chat(text) -->

<!-- > > > response = openai_summarize_text(text) -->
