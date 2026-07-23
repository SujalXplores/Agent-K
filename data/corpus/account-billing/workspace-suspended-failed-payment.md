# My workspace was suspended for non-payment - what now

A workspace is suspended after all three automatic payment retries fail and the subsequent 7-day grace period elapses with no successful charge. Suspension blocks all member access (including the workspace owner) to boards, tasks, and the API - you'll see a dedicated "Workspace suspended" screen instead of the normal login redirect.

No data is deleted during suspension. Projects, tasks, comments, attachments, and integration configurations are all preserved exactly as they were at the moment of suspension, and reactivating billing restores full access with zero data loss.

To reactivate: log in as the workspace owner (owner login still works specifically to reach the billing-recovery flow), go to the suspended screen's "Update payment" link, enter a valid payment method, and click "Reactivate workspace". The charge for the overdue period plus the current period is processed immediately.

If reactivation still fails after entering a new card, it usually means the card was declined again - check Invoice History for the specific decline reason, or contact billing support directly if the decline code is unclear. Workspaces suspended for more than 90 days may have their data archived to cold storage and require a support ticket to restore, so don't let a suspension sit unresolved for an extended period.
