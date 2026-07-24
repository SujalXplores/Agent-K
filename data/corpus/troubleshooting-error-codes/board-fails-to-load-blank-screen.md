# Troubleshooting: board loads blank / white screen

A blank board screen with no error message is almost always a client-side rendering issue rather than a data problem - your task data is safe and unaffected regardless of what the screen shows. Start by opening your browser's developer console (F12) and checking for red error text, which usually names the specific failing component.

The most common cause is a stale cached version of Flowdeck's frontend JavaScript conflicting with a newer backend API response shape after a recent Flowdeck release. A hard refresh (Ctrl+Shift+R or Cmd+Shift+R) clears this in the majority of cases by forcing the browser to re-download the current frontend assets instead of using cached ones.

If a hard refresh doesn't resolve it, try loading the board in a private/incognito window - this rules out a misbehaving browser extension (ad blockers and privacy extensions are the most common offenders we see, since they sometimes block Flowdeck's WebSocket connection used for live board updates).

If the board loads fine in incognito but not your normal profile, disable extensions one at a time in your normal profile to identify the culprit rather than disabling all of them at once, which makes it harder to pin down which specific extension was interfering.
