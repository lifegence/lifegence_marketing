app_name = "lifegence_marketing"
app_title = "Lifegence Marketing"
app_publisher = "Lifegence Corporation"
app_description = "Advertising and campaign management: budgets, tracking links, ad performance and ROI"
app_email = "noreply@lifegence.com"
app_license = "apache-2.0"

# Apps
# ------------------

required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lifegence_marketing",
# 		"logo": "/assets/lifegence_marketing/logo.png",
# 		"title": "Lifegence Marketing",
# 		"route": "/lifegence_marketing",
# 		"has_permission": "lifegence_marketing.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `lifegence_marketing/dock/lifegence_marketing/lifegence_marketing.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lifegence_marketing/css/lifegence_marketing.css"
# app_include_js = "/assets/lifegence_marketing/js/lifegence_marketing.js"

# include js, css files in header of web template
# web_include_css = "/assets/lifegence_marketing/css/lifegence_marketing.css"
# web_include_js = "/assets/lifegence_marketing/js/lifegence_marketing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lifegence_marketing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "lifegence_marketing/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "lifegence_marketing.utils.jinja_methods",
# 	"filters": "lifegence_marketing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "lifegence_marketing.install.before_install"
# after_install = "lifegence_marketing.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "lifegence_marketing.uninstall.before_uninstall"
# after_uninstall = "lifegence_marketing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lifegence_marketing.utils.before_app_install"
# after_app_install = "lifegence_marketing.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lifegence_marketing.utils.before_app_uninstall"
# after_app_uninstall = "lifegence_marketing.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "lifegence_marketing.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "lifegence_marketing.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lifegence_marketing.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["lifegence_marketing.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lifegence_marketing.tasks.all"
# 	],
# 	"daily": [
# 		"lifegence_marketing.tasks.daily"
# 	],
# 	"hourly": [
# 		"lifegence_marketing.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lifegence_marketing.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lifegence_marketing.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lifegence_marketing.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "lifegence_marketing.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lifegence_marketing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lifegence_marketing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lifegence_marketing.utils.before_request"]
# after_request = ["lifegence_marketing.utils.after_request"]

# Job Events
# ----------
# before_job = ["lifegence_marketing.utils.before_job"]
# after_job = ["lifegence_marketing.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"lifegence_marketing.auth.validate"
# ]

# on_social_login = "lifegence_marketing.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


app_logo_url = "/assets/lifegence_marketing/images/logo.svg"
app_home = "/desk/marketing"

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": app_logo_url,
		"title": app_title,
		"route": app_home,
		"has_permission": "frappe.permissions.check_app_permission",
	}
]

after_install = "lifegence_marketing.setup.after_install"
after_migrate = "lifegence_marketing.setup.after_migrate"
after_app_install = "lifegence_marketing.setup.after_app_install"

website_route_rules = [{"from_route": "/m/<code>", "to_route": "m"}]

after_request = ["lifegence_marketing.attribution.after_request"]

doc_events = {
	"Lead": {
		"before_insert": "lifegence_marketing.attribution.before_insert_lead",
		"after_insert": "lifegence_marketing.attribution.after_insert_lead",
	},
	"CRM Lead": {
		"before_insert": "lifegence_marketing.attribution.before_insert_lead",
		"after_insert": "lifegence_marketing.attribution.after_insert_lead",
	},
	"CRM Deal": {"before_insert": "lifegence_marketing.attribution.before_insert_deal"},
	"Ringi": {
		"on_update": "lifegence_marketing.marketing.doctype.marketing_campaign.marketing_campaign.on_ringi_update"
	},
}

scheduler_events = {
	"daily": ["lifegence_marketing.connectors.sync.daily"],
	"hourly": ["lifegence_marketing.connectors.sync.retry_failed"],
}
