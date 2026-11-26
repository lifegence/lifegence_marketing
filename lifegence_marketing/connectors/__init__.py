# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Connector framework: the contract between Lifegence Marketing and the channels' APIs.

A connector app registers its connectors in hooks.py:

	marketing_connectors = {"meta": "my_app.meta.MetaConnector"}

and each connector subclasses MarketingConnector (base.py). The framework schedules the imports, writes the figures
(lifegence_marketing.performance.Saver), creates leads, keeps a log and tells people when something fails. A connector
only talks to its API and returns plain data.
"""

import frappe


def registry():
	"""{key: dotted path} from every installed app's marketing_connectors hook (later apps override earlier ones)."""
	hooks = frappe.get_hooks("marketing_connectors") or {}
	# get_hooks merges dict hooks into {key: [path, ...]}; the last installed app wins
	return {key: (paths[-1] if isinstance(paths, list) else paths) for key, paths in hooks.items()}


def get_connector(key):
	path = registry().get(key)
	if not path:
		frappe.throw(frappe._("No connector {0} is installed").format(key))
	return frappe.get_attr(path)()
