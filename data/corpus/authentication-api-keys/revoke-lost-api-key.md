# I think an API key was leaked - how do I revoke it

Go to Workspace Settings > Developer > API Keys, find the key by its label, and click "Revoke" - this takes effect within a few seconds and any in-flight requests using that key will start failing with 401 immediately. Revocation cannot be undone; you'll need to generate a new key and update every integration that used the old one.
