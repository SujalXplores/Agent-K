# Troubleshooting: a member says they can't see a project they should have access to

The most common cause is that the member was added to the workspace but never explicitly invited to the specific project - per the permission-inheritance model, workspace membership alone grants zero project visibility by default. Check the project's Members tab to confirm they're actually listed there, not just in the workspace-wide member list under Workspace Settings > Members.

If they are listed on the project but still can't see it, check whether they're a Guest account rather than a full Member - guests only see projects they were invited to as a guest specifically, and if a regular Member was later converted to a Guest role (which can happen during an offboarding-to-contractor transition), their prior implicit workspace-wide project directory visibility is revoked even though their explicit per-project grants remain.

If the member is a SCIM-provisioned user (see scim-provisioning-setup), confirm their IdP group membership actually maps to a role with access to that project - SCIM sync only manages workspace-level role assignment via group mapping, not automatic project-level access, so a newly SCIM-provisioned member still needs an explicit project invitation just like a manually-created member would.

Finally, check whether the project itself was archived (see archiving-vs-deleting-projects) - archived projects disappear from every member's active projects list, including members with full access, and are only visible again via Workspace Settings > Archived Projects or after being unarchived. This is a frequent false alarm that looks exactly like a permissions bug but isn't one.
