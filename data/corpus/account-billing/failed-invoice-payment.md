# Troubleshooting: my invoice payment failed

When an invoice payment fails, Flowdeck retries the charge automatically three times over five days: immediately, then after 48 hours, then after 96 hours. You will see a yellow "Payment issue" banner in your workspace during this window, and the workspace owner receives an email after each failed attempt with the decline reason returned by the card network.

The most common decline reasons are an expired card, insufficient funds, or the issuing bank flagging the charge as suspicious because it's a recurring SaaS billing pattern. Check Workspace Settings > Billing > Invoice History for the specific decline code attached to the failed attempt before contacting your bank.

To resolve it yourself: update the card under Payment Method, then click "Retry now" on the failed invoice rather than waiting for the next scheduled retry - this triggers an immediate re-charge attempt against the new card.

If all three automatic retries fail, the workspace moves into a 7-day grace period during which all features keep working but a persistent banner is shown to every member. After the grace period expires with no successful payment, the workspace is suspended (see the workspace-suspended-failed-payment guide) - projects and data are preserved but access is blocked until payment succeeds.
