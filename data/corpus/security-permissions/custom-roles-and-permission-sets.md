# Creating custom roles and permission sets

Enterprise plans support custom roles beyond the built-in Admin / Editor / Viewer set, defined under Workspace Settings > Security > Custom Roles as a named combination of granular permissions (e.g. "can edit tasks" without "can delete tasks", or "can view reports" without "can edit automations").

Custom roles can be assigned at the project level just like built-in roles, and can also be mapped to SCIM/SSO groups the same way built-in roles can (see scim-provisioning-setup), so an organization can replicate a fine-grained internal RBAC model rather than being limited to Flowdeck's three default tiers.
