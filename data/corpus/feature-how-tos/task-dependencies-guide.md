# Setting task dependencies

Open a task's detail panel and use "Add dependency" to mark it as blocked-by another task. A blocked task shows a small lock icon on its card and, depending on your project's settings, can be prevented from being moved to Done until its blocking task is completed first.

Circular dependencies (Task A blocks B, B blocks A) are rejected at creation time with an explanatory error rather than silently accepted, since Flowdeck's due-date scheduling logic assumes a strict dependency ordering and cannot resolve a cycle.
